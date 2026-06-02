# Cookie auth handoff

## Why cookie-handoff, not SSO-in-Playwright

Kai's Honeycomb login is Google SSO to `coilysiren@gmail.com`. Logging in from a fresh Playwright Chrome means Claude touches that Google session. Copying a Honeycomb cookie out of an already-authenticated browser hands over a Honeycomb-scoped session only, with no path back to Google. Stronger security story for the same automation surface.

## One-time auth handoff

When the skill fires with no usable cookie in SSM (first run, or expired), walk Kai through these steps and pause until done.

Honeycomb's login flow embeds Google SSO, so a logged-in reload of `ui.honeycomb.io` shows requests to **both** `ui.honeycomb.io` **and** `accounts.google.com` in the Network panel. Copying the Cookie header from the wrong row produces a silent failure: the cookie stashes, `build-honeycomb-storage` writes the file, Playwright loads, and navigation just redirects to `/login`. Filter discipline is load-bearing.

1. Open `https://ui.honeycomb.io/` in her main browser (already logged in).
2. **DevTools → Network tab → type `ui.honeycomb.io` into the filter box → reload the page → click any request in the filtered list.** The filter is the step that prevents the wrong-row copy.
3. Under **Request Headers**, find the `Cookie:` line. Copy the entire value (everything after `Cookie: `, no leading space, no trailing newline). Verify the copied string contains the substring `hny=`, that is Honeycomb's session cookie. If it doesn't, you're looking at a Google-SSO row. Go back to step 2 and re-filter.
4. Drop the value into a temp file (avoids long-secret-in-argv hazards) and stash:
   ```
   coily ops aws ssm put-parameter --overwrite --name /coilysiren/honeycomb/session-cookie --type SecureString --value file:///tmp/honeycomb-cookie.txt
   shred -u /tmp/honeycomb-cookie.txt
   ```
5. Rebuild the Playwright storage-state file from the new SSM value:
   ```
   coily exec build-honeycomb-storage
   ```
   (Once [agentic-os-kai#652](https://github.com/coilysiren/agentic-os-kai/issues/652) lands, this command will refuse to write the file if the cookie value lacks `hny=`, so a malformed handoff fails fast at build time rather than at navigation time.)
6. Cookie has a finite lifetime (typically hours to days). When the skill detects a redirect to `/login`, prompt for a fresh copy.
