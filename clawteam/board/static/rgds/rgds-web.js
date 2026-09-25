import { jsxs as i, jsx as a } from "react/jsx-runtime";
const c = [
  "primary-light",
  "secondary-light",
  "primary-dark",
  "secondary-dark"
];
function h(e, r = document.documentElement) {
  r.setAttribute("data-theme", e);
  try {
    localStorage.setItem("rgds-theme", e);
  } catch {
  }
}
function p() {
  try {
    const e = localStorage.getItem("rgds-theme");
    if (e && c.includes(e))
      return e;
  } catch {
  }
  return null;
}
function s(...e) {
  return e.filter(Boolean).join(" ");
}
function o({
  variant: e = "filled",
  selected: r,
  className: t,
  children: d,
  ...l
}) {
  return /* @__PURE__ */ a(
    "button",
    {
      type: "button",
      className: s("md-btn", "rgds-interactive", `rgds-btn--${e}`, t),
      "aria-pressed": r || void 0,
      ...l,
      children: d
    }
  );
}
function R({
  className: e,
  children: r,
  ...t
}) {
  return /* @__PURE__ */ a(
    "button",
    {
      type: "button",
      className: s("rgds-icon-btn", "rgds-interactive", e),
      ...t,
      children: r
    }
  );
}
function N({
  interactive: e = !1,
  className: r,
  children: t,
  onClick: d
}) {
  return /* @__PURE__ */ a(
    e ? "button" : "div",
    {
      className: s("md-card", e && "rgds-interactive", r),
      "data-interactive": e ? "true" : void 0,
      onClick: d,
      type: e ? "button" : void 0,
      children: t
    }
  );
}
function u({
  label: e,
  id: r,
  className: t,
  ...d
}) {
  const l = r || d.name;
  return /* @__PURE__ */ i("label", { className: s("rgds-field", t), children: [
    e ? /* @__PURE__ */ a("span", { className: "rgds-field__label", children: e }) : null,
    /* @__PURE__ */ a("input", { id: l, className: "rgds-field__input rgds-interactive", ...d })
  ] });
}
function x(e) {
  return /* @__PURE__ */ a(u, { ...e, type: "search", className: s("rgds-search", e.className) });
}
function S({
  label: e,
  className: r,
  ...t
}) {
  return /* @__PURE__ */ i("label", { className: s("rgds-check", "rgds-interactive", r), children: [
    /* @__PURE__ */ a("input", { type: "checkbox", ...t }),
    e ? /* @__PURE__ */ a("span", { children: e }) : null
  ] });
}
function v({
  label: e,
  className: r,
  ...t
}) {
  return /* @__PURE__ */ i("label", { className: s("rgds-switch", r), children: [
    /* @__PURE__ */ a("input", { type: "checkbox", role: "switch", className: "rgds-interactive", ...t }),
    e ? /* @__PURE__ */ a("span", { children: e }) : null
  ] });
}
function C({
  selected: e,
  className: r,
  children: t,
  ...d
}) {
  return /* @__PURE__ */ a(
    "button",
    {
      type: "button",
      role: "tab",
      "aria-selected": e || void 0,
      className: s("rgds-tab", "rgds-interactive", r),
      ...d,
      children: t
    }
  );
}
function A({ children: e, className: r }) {
  return /* @__PURE__ */ a("div", { role: "tablist", className: s("rgds-tabs", r), children: e });
}
function D({ children: e, className: r }) {
  return /* @__PURE__ */ a("nav", { className: s("rgds-bottom-nav", r), "aria-label": "Primary", children: e });
}
function y({ children: e, className: r }) {
  return /* @__PURE__ */ a("nav", { className: s("rgds-nav-rail", r), "aria-label": "Primary", children: e });
}
function K({
  current: e,
  className: r,
  children: t,
  ...d
}) {
  return /* @__PURE__ */ a(
    "button",
    {
      type: "button",
      className: s("rgds-nav-item", "rgds-interactive", r),
      "aria-current": e ? "page" : void 0,
      ...d,
      children: t
    }
  );
}
function k({ children: e, className: r }) {
  return /* @__PURE__ */ a("span", { className: s("rgds-badge", r), children: e });
}
function F({
  tone: e = "info",
  children: r,
  className: t
}) {
  return /* @__PURE__ */ a("div", { role: "status", className: s("rgds-alert", `rgds-alert--${e}`, t), children: r });
}
function I({
  open: e,
  title: r,
  children: t,
  onClose: d,
  className: l
}) {
  return e ? /* @__PURE__ */ a("div", { className: "rgds-dialog-scrim", role: "presentation", onClick: d, children: /* @__PURE__ */ i(
    "div",
    {
      role: "dialog",
      "aria-modal": "true",
      className: s("rgds-dialog", l),
      onClick: (g) => g.stopPropagation(),
      children: [
        r ? /* @__PURE__ */ a("h2", { className: "rgds-dialog__title", children: r }) : null,
        /* @__PURE__ */ a("div", { className: "rgds-dialog__body", children: t })
      ]
    }
  ) }) : null;
}
function T({
  open: e,
  children: r,
  onClose: t,
  className: d
}) {
  return e ? /* @__PURE__ */ a("div", { className: "rgds-drawer-scrim", onClick: t, children: /* @__PURE__ */ a("aside", { className: s("rgds-drawer", d), onClick: (l) => l.stopPropagation(), children: r }) }) : null;
}
function M({ children: e, className: r }) {
  return /* @__PURE__ */ a("header", { className: s("rgds-appbar", r), children: e });
}
function m({
  selected: e,
  className: r,
  children: t,
  ...d
}) {
  return /* @__PURE__ */ a(
    "button",
    {
      type: "button",
      className: s("rgds-list-tile", "rgds-interactive", r),
      "aria-selected": e || void 0,
      ...d,
      children: t
    }
  );
}
function w(e) {
  return /* @__PURE__ */ a(m, { ...e, className: s("rgds-menu-item", e.className) });
}
function E({
  children: e,
  className: r,
  selected: t,
  onClick: d
}) {
  return /* @__PURE__ */ a(
    "button",
    {
      type: "button",
      className: s("rgds-chip", "rgds-interactive", r),
      "aria-pressed": t || void 0,
      onClick: d,
      children: e
    }
  );
}
function _({ children: e, className: r }) {
  return /* @__PURE__ */ a("div", { role: "status", className: s("rgds-toast", r), children: e });
}
function G({
  label: e,
  children: r,
  className: t
}) {
  return /* @__PURE__ */ a("span", { className: s("rgds-tooltip", t), "data-tooltip": e, children: r });
}
function O({
  value: e = 0,
  className: r
}) {
  const t = Math.max(0, Math.min(100, e));
  return /* @__PURE__ */ a(
    "div",
    {
      className: s("rgds-progress", r),
      role: "progressbar",
      "aria-valuenow": t,
      "aria-valuemin": 0,
      "aria-valuemax": 100,
      children: /* @__PURE__ */ a("div", { className: "rgds-progress__bar", style: { width: `${t}%` } })
    }
  );
}
function j({
  className: e
}) {
  return /* @__PURE__ */ a(
    "div",
    {
      className: s("rgds-progress-circular", e),
      role: "progressbar",
      "aria-valuetext": "loading"
    }
  );
}
function W({
  page: e,
  pages: r,
  onChange: t,
  className: d
}) {
  return /* @__PURE__ */ i("nav", { className: s("rgds-pagination", d), "aria-label": "Pagination", children: [
    /* @__PURE__ */ a(
      o,
      {
        variant: "outlined",
        disabled: e <= 1,
        onClick: () => t == null ? void 0 : t(e - 1),
        children: "Prev"
      }
    ),
    /* @__PURE__ */ i("span", { className: "rgds-pagination__status", children: [
      e,
      " / ",
      r
    ] }),
    /* @__PURE__ */ a(
      o,
      {
        variant: "outlined",
        disabled: e >= r,
        onClick: () => t == null ? void 0 : t(e + 1),
        children: "Next"
      }
    )
  ] });
}
function P({
  children: e,
  className: r
}) {
  return /* @__PURE__ */ a("div", { className: s("rgds-table-wrap", r), children: /* @__PURE__ */ a("table", { className: "rgds-table", children: e }) });
}
function U(e) {
  return /* @__PURE__ */ a("th", { ...e, className: s("rgds-th", e.className) });
}
function q(e) {
  return /* @__PURE__ */ a("td", { ...e, className: s("rgds-td", e.className) });
}
function B({
  sidebar: e,
  children: r,
  className: t
}) {
  return /* @__PURE__ */ i("div", { className: s("md-shell", t), children: [
    e ? /* @__PURE__ */ a("aside", { className: "md-sidebar", children: e }) : null,
    /* @__PURE__ */ a("main", { className: "md-main", children: r })
  ] });
}
function L({
  appBar: e,
  sidebar: r,
  rail: t,
  bottomNav: d,
  children: l,
  className: g
}) {
  return /* @__PURE__ */ i("div", { className: s("rgds-shell", "rgds-shell--adaptive", g), children: [
    e,
    /* @__PURE__ */ i("div", { className: "rgds-shell__body", children: [
      r ? /* @__PURE__ */ a("aside", { className: "rgds-shell__sidebar md-sidebar", children: r }) : null,
      t ? /* @__PURE__ */ a("nav", { className: "rgds-shell__rail rgds-nav-rail", children: t }) : null,
      /* @__PURE__ */ a("main", { className: "rgds-shell__main md-main", children: l })
    ] }),
    d ? /* @__PURE__ */ a("nav", { className: "rgds-shell__bottom-nav rgds-bottom-nav", "aria-label": "Primary", children: d }) : null
  ] });
}
function $({
  master: e,
  detail: r,
  detailOpen: t = !0,
  className: d
}) {
  return /* @__PURE__ */ i("div", { className: s("rgds-master-detail", d), children: [
    /* @__PURE__ */ a("div", { className: "rgds-master-detail__master", children: e }),
    /* @__PURE__ */ a("div", { className: "rgds-master-detail__detail", "data-open": t ? "true" : "false", children: r })
  ] });
}
function H({ children: e, className: r }) {
  return /* @__PURE__ */ a("div", { className: s("rgds-form-layout", r), children: e });
}
function V({ children: e, className: r }) {
  return /* @__PURE__ */ a("div", { className: s("rgds-toolbar", r), children: e });
}
function Y({ children: e, className: r }) {
  return /* @__PURE__ */ a("div", { className: s("rgds-card-grid md-grid", r), children: e });
}
const z = {
  "RGDS / Button": {
    figmaNodeId: "1:31",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsButton",
    flutterWidget: "RgdsButton",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Card / Interactive": {
    figmaNodeId: "2:20",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsCard",
    flutterWidget: "RgdsCard",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Text Field": {
    figmaNodeId: "6:18",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsTextField",
    flutterWidget: "RgdsTextField",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Checkbox": {
    figmaNodeId: "6:37",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsCheckbox",
    flutterWidget: "RgdsCheckbox",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Switch": {
    figmaNodeId: "6:56",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsSwitch",
    flutterWidget: "RgdsSwitch",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Tab": {
    figmaNodeId: "6:69",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsTab",
    flutterWidget: "RgdsTab",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Nav Item": {
    figmaNodeId: "6:88",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsNavItem",
    flutterWidget: "RgdsNavItem",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Badge": {
    figmaNodeId: "6:101",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsBadge",
    flutterWidget: "RgdsBadge",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Alert": {
    figmaNodeId: "6:126",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsAlert",
    flutterWidget: "RgdsAlert",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Dialog": {
    figmaNodeId: "6:163",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsDialog",
    flutterWidget: "RgdsDialog",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / App Bar": {
    figmaNodeId: "6:182",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsAppBar",
    flutterWidget: "RgdsAppBar",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / List Tile": {
    figmaNodeId: "6:213",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsListTile",
    flutterWidget: "RgdsListTile",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Icon Button": {
    figmaNodeId: "6:226",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsIconButton",
    flutterWidget: "RgdsIconButton",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Toast": {
    figmaNodeId: "8:268",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsToast",
    flutterWidget: "RgdsToast",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Tooltip": {
    figmaNodeId: "8:281",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsTooltip",
    flutterWidget: "RgdsTooltip",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Progress Linear": {
    figmaNodeId: "8:300",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsProgress",
    flutterWidget: "RgdsProgress",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Progress Circular": {
    figmaNodeId: "8:319",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsProgressCircular",
    flutterWidget: "RgdsProgressCircular",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Pagination": {
    figmaNodeId: "8:88",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsPagination",
    flutterWidget: "RgdsPagination",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Drawer": {
    figmaNodeId: "8:143",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsDrawer",
    flutterWidget: "RgdsDrawer",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Menu Item": {
    figmaNodeId: "8:162",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsMenuItem",
    flutterWidget: "RgdsMenuItem",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Data Table": {
    figmaNodeId: "8:217",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsTable",
    flutterWidget: "RgdsDataTable",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Search Field": {
    figmaNodeId: "8:236",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsSearchField",
    flutterWidget: "RgdsSearchField",
    package: "@r3lentless/rgds-web"
  },
  "RGDS / Chip": {
    figmaNodeId: "8:249",
    fileKey: "KbhSAUCrADaqhxOm7jM2FC",
    reactExport: "RgdsChip",
    flutterWidget: "RgdsChip",
    package: "@r3lentless/rgds-web"
  }
}, n = {
  xs: 0,
  sm: 600,
  md: 905,
  lg: 1240,
  xl: 1440,
  mobile: 600,
  tablet: 1240,
  desktop: 1240
}, f = {
  mobile: 390,
  tabletPortrait: 834,
  tabletLandscape: 1194,
  desktop: 1440
};
function J(e) {
  return e < n.mobile ? "mobile" : e < n.tablet ? "tablet" : "desktop";
}
function Q(e) {
  return e < n.mobile ? "bottom" : e < n.md ? "drawer" : e < n.desktop ? "rail" : "sidebar";
}
function X(e) {
  const r = Object.entries(f);
  return r.sort((t, d) => Math.abs(t[1] - e) - Math.abs(d[1] - e)), r[0][0];
}
function Z(e = typeof document < "u" ? document.documentElement : {}) {
  if (!("style" in e) && !e.documentElement) return null;
  const r = "documentElement" in e ? e.documentElement : e, t = getComputedStyle(r).getPropertyValue("--md-rgds-form-factor").trim();
  return t === "mobile" || t === "tablet" || t === "desktop" ? t : null;
}
export {
  z as FIGMA_COMPONENT_MAP,
  n as RGDS_BREAKPOINTS,
  f as RGDS_LAYOUT_TARGETS,
  c as RGDS_THEMES,
  L as RgdsAdaptiveShell,
  F as RgdsAlert,
  M as RgdsAppBar,
  B as RgdsAppShell,
  k as RgdsBadge,
  D as RgdsBottomNav,
  o as RgdsButton,
  N as RgdsCard,
  Y as RgdsCardGrid,
  S as RgdsCheckbox,
  E as RgdsChip,
  I as RgdsDialog,
  T as RgdsDrawer,
  H as RgdsFormLayout,
  R as RgdsIconButton,
  m as RgdsListTile,
  $ as RgdsMasterDetail,
  w as RgdsMenuItem,
  K as RgdsNavItem,
  y as RgdsNavRail,
  W as RgdsPagination,
  O as RgdsProgress,
  j as RgdsProgressCircular,
  x as RgdsSearchField,
  v as RgdsSwitch,
  C as RgdsTab,
  P as RgdsTable,
  A as RgdsTabs,
  q as RgdsTd,
  u as RgdsTextField,
  U as RgdsTh,
  _ as RgdsToast,
  V as RgdsToolbar,
  G as RgdsTooltip,
  h as applyRgdsTheme,
  Z as readRgdsFormFactorFromCss,
  p as readStoredRgdsTheme,
  J as rgdsFormFactorForWidth,
  X as rgdsLayoutTargetForWidth,
  Q as rgdsNavModeForWidth
};
