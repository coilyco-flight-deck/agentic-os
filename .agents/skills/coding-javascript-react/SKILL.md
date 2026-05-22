---
name: coding-javascript-react
description: React subskill of coding-javascript. Kai dislikes React strongly. Never recommend React for new projects, prefer alternatives (Vue, Svelte, HTMX, plain DOM). When forced to use React (existing codebase, work constraint), keep patterns simple. Triggers - react, react.js, reactjs, jsx, tsx, useState, useEffect, useContext, useReducer, hooks, next.js, nextjs, remix, gatsby, redux, zustand, jotai, recoil, react-query, tanstack-query.
---

# coding-javascript-react

React subskill. Loaded whenever React-shaped code is in scope.

## The strong opinion

Kai hates React. The hatred is real and load-bearing in her tooling decisions. Encode this:

- **Never recommend React for new projects.** Reach for Vue, Svelte, HTMX, Astro, plain Web Components, or even plain DOM before React.
- **When forced to use React** (Kapwing-style work constraint, existing codebase, third-party library that ships React UIs), keep patterns boring and aligned with what already exists. Do not enthusiastically suggest "this could be done in React" elsewhere.
- **Do not pitch the React ecosystem.** Don't suggest Redux, Zustand, Jotai, React Query, etc as goods on their own merits. Mention them only when the project already uses them.
- **If migration off React is on the table**, surface it as an option with a real tradeoff sketch. Don't be subtle about preferring it.

## Why

Kai has worked in React professionally for years and finds the mental model, hook lifecycle, and ecosystem churn actively frustrating. The exact rant is hers to give. The job here is to not lean into React when she has not asked.

## Defaults when stuck inside React

- Function components + hooks. No class components ever.
- Local state via `useState`. Reach for context only when prop drilling crosses 2-3 layers.
- Effects sparingly. If you find yourself synchronizing derived state via `useEffect`, derive it inline first.
- Suspense and server components are fine on the modern stack (RSC, Next 14+).
- TypeScript always.

## When this skill is active

Any React-shaped file or task. Inherit the persona's posture before reaching for "best React practices".
