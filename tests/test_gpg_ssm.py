"""Tests for scripts/gpg-ssm."""
from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "gpg-ssm"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _make_stubs(root: Path) -> tuple[Path, Path, Path, Path, Path]:
    bin_dir = root / "bin"
    bin_dir.mkdir()

    aws_log = root / "aws.log"
    gpg_log = root / "gpg.log"
    import_log = root / "import.log"
    passphrase_log = root / "passphrase.log"
    key_present = root / "key-present"
    aws_log.touch()
    gpg_log.touch()

    _write_executable(
        bin_dir / "aws",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            printf '%s\\n' "$*" >> {aws_log!s}
            if [[ "${{1:-}}" == sts && "${{2:-}}" == get-caller-identity ]]; then
              if [[ "${{FAKE_AWS_STS_FAIL:-0}}" == 1 ]]; then
                exit 1
              fi
              exit 0
            fi
            if [[ "${{1:-}}" == ssm && "${{2:-}}" == get-parameter ]]; then
              name=""
              shift 2
              while [[ $# -gt 0 ]]; do
                case "$1" in
                  --name)
                    name="$2"
                    shift 2
                    ;;
                  --query|--output)
                    shift 2
                    ;;
                  --with-decryption)
                    shift 1
                    ;;
                  *)
                    shift
                    ;;
                esac
              done
              case "$name" in
                /coilysiren/gpg-secret-key)
                  printf '%s' "${{FAKE_GPG_SECRET_KEY:-}}"
                  ;;
                /coilysiren/gpg-passphrase)
                  printf '%s' "${{FAKE_GPG_PASSPHRASE:-}}"
                  ;;
                *)
                  exit 1
                  ;;
              esac
              exit 0
            fi
            echo "unexpected aws invocation: $*" >&2
            exit 1
            """
        ),
    )

    _write_executable(
        bin_dir / "gpg",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            printf '%s\\n' "$*" >> {gpg_log!s}
            if [[ " $* " == *" --list-secret-keys "* ]]; then
              if [[ -f {key_present!s} ]]; then
                printf 'sec::::::::::::::\\n'
                exit 0
              fi
              exit 1
            fi
            if [[ " $* " == *" --import "* ]]; then
              cat > {import_log!s}
              touch {key_present!s}
              exit 0
            fi
            if [[ " $* " == *" --passphrase-fd 3 "* ]]; then
              cat <&3 > {passphrase_log!s}
              exit 0
            fi
            exit 0
            """
        ),
    )

    return bin_dir, aws_log, gpg_log, import_log, passphrase_log


def _run(root: Path, *args: str, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    bin_dir, aws_log, gpg_log, import_log, passphrase_log = _make_stubs(root)
    git_config = root / "gitconfig"
    git_config.write_text("[user]\n\tsigningkey = ABCDEF1234567890\n", encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "GIT_CONFIG_GLOBAL": str(git_config),
            "FAKE_GPG_SECRET_KEY": (
                "-----BEGIN PGP PRIVATE KEY BLOCK-----\n"
                "fake-secret-key\n"
                "-----END PGP PRIVATE KEY BLOCK-----\n"
            ),
            "FAKE_GPG_PASSPHRASE": "shared-passphrase",
        }
    )
    env.update(env_overrides)
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_passthrough_non_signing_invocations(tmp_path: Path) -> None:
    result = _run(tmp_path, "--verify", "artifact.sig")

    assert result.returncode == 0
    assert (tmp_path / "aws.log").read_text(encoding="utf-8") == ""
    assert (tmp_path / "gpg.log").read_text(encoding="utf-8").strip() == "--verify artifact.sig"


def test_bootstraps_shared_secret_key_when_missing(tmp_path: Path) -> None:
    result = _run(tmp_path, "--clearsign")

    assert result.returncode == 0
    assert (tmp_path / "aws.log").read_text(encoding="utf-8").splitlines() == [
        "sts get-caller-identity",
        "ssm get-parameter --name /coilysiren/gpg-secret-key --with-decryption --query Parameter.Value --output text",
        "ssm get-parameter --name /coilysiren/gpg-passphrase --with-decryption --query Parameter.Value --output text",
    ]
    assert (tmp_path / "import.log").read_text(encoding="utf-8").startswith("-----BEGIN PGP PRIVATE KEY BLOCK-----")
    assert (tmp_path / "passphrase.log").read_text(encoding="utf-8") == "shared-passphrase"
    assert "--import" in (tmp_path / "gpg.log").read_text(encoding="utf-8")
    assert "--clearsign" in (tmp_path / "gpg.log").read_text(encoding="utf-8")


def test_gates_on_aws_credentials_before_fetching_ssm(tmp_path: Path) -> None:
    result = _run(tmp_path, "--clearsign", FAKE_AWS_STS_FAIL="1")

    assert result.returncode == 1
    assert (tmp_path / "aws.log").read_text(encoding="utf-8").splitlines() == [
        "sts get-caller-identity",
    ]
    assert not (tmp_path / "import.log").exists()
    assert not (tmp_path / "passphrase.log").exists()
    assert "--import" not in (tmp_path / "gpg.log").read_text(encoding="utf-8")
