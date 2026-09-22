import {copyFileSync, mkdirSync} from "node:fs";
import {createRequire} from "node:module";
import path from "node:path";

// Next's asset loader does not emit the worker's relative shared-module import.
// Serve both package files together, always from the installed lockfile version.
const root = path.dirname(createRequire(import.meta.url).resolve("maplibre-gl/package.json"));
const destination = path.join(process.cwd(), "public", "maplibre");
mkdirSync(destination, {recursive: true});
for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(path.join(root, "dist", file), path.join(destination, file));
}
copyFileSync(path.join(root, "LICENSE.txt"), path.join(destination, "LICENSE.txt"));
