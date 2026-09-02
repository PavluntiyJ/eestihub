// Shared between the server layout's pre-paint script and the client toggle,
// so it must not live in a "use client" module: constants exported from one
// are not resolvable on the server.
export const THEME_STORAGE_KEY = "eestihub-theme";
