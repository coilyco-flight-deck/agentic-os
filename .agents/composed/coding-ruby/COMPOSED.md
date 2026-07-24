---
name: coding-ruby
description: Ruby umbrella skill. Kai was an OSS engineer at Ruby Together (2016) maintaining RubyGems and Bundler - defer to her instinct over generic Ruby guidance.
low-context: required
seed:
  kind: language
  language: ruby
  extensions: [".rb"]
---

# coding-ruby

Umbrella for any Ruby work. Mostly historical at this point - Kai was an Open Source Software Engineer at Ruby Together (2016) maintaining RubyGems and Bundler. Active Ruby work is rare in current rotation.

## Defaults

- **Version**: whatever the project pins. Don't suggest upgrades unless asked.
- **Package manager**: `bundler`. Lock files are sacred.
- **Tests**: project's own (RSpec or Minitest). Don't impose.
- **Style**: project's own `.rubocop.yml`. Don't impose.

## Posture

This skill is mostly a placeholder. Kai's instinct on Ruby code is sharper than training-data defaults. When she's editing Ruby, she's leading. Stay in support mode.

## When this skill is active

Any Ruby file or task. Inherit Kai's posture before reaching for generic Ruby guidance.

## Triggers

ruby, .rb, rubygems, bundler, gem, gemfile, rake, rails, sinatra, rspec, minitest, sidekiq, rbenv, rvm, asdf-ruby.
