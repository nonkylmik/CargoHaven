// Run with: npm run test:unit
// The product is named CargoHaven (formerly SeaShield). Every page title, the app header and the sign-in screen
// show the new name; the former name stays only in compatibility identifiers such as source folder names.
import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import { after, test } from "node:test";
import { fileURLToPath } from "node:url";

import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { createServer } from "vite";

const root = fileURLToPath(new URL("../../../", import.meta.url));
const vite = await createServer({
  root,
  configFile: false,
  appType: "custom",
  logLevel: "error",
  server: { middlewareMode: true, hmr: false, watch: null },
  resolve: { alias: { "@": `${root}src` } },
});
after(() => vite.close());

// SeaShield is the former name; Marisentry was a working name dropped before release.
const FORMER_NAME = /sea\s*shield|marisentry/i;
const routeFiles = readdirSync(`${root}src/routes`).filter((f) => f.endsWith(".tsx"));

test("every route's head metadata names CargoHaven and never the former name", async () => {
  // __root.tsx sets shared metadata only; every other route module is a page that must set its own title.
  const pages = routeFiles.filter((f) => f !== "__root.tsx");
  assert.ok(pages.length >= 13, `route modules found: ${routeFiles.join(", ")}`);
  for (const file of routeFiles) {
    const { Route } = await vite.ssrLoadModule(`/src/routes/${file}`);
    const head = Route.options.head?.({});
    assert.doesNotMatch(JSON.stringify(head ?? {}), FORMER_NAME, file);
    if (file === "__root.tsx") continue;
    const title = head?.meta?.find((m) => m.title)?.title;
    assert.match(title ?? "", /CargoHaven/, `${file} must set a page title that names CargoHaven`);
  }
});

test("the app header and sign-in screen show the CargoHaven wordmark", async () => {
  const { BrandLockup } = await vite.ssrLoadModule("/src/components/seashield/BrandMark.tsx");
  const { LoginScreen } = await vite.ssrLoadModule("/src/components/seashield/LoginScreen.tsx");
  const lockup = renderToString(
    createElement(BrandLockup, { subtitle: "Maritime Security Operations" }),
  );
  assert.match(lockup, /CARGOHAVEN/);
  const login = renderToString(createElement(LoginScreen, { onLogin: async () => {} }));
  assert.match(login, /CARGOHAVEN/);
  assert.doesNotMatch(login, FORMER_NAME);
});
