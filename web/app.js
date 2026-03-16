const form = document.querySelector("#planner-form");
const summaryEl = document.querySelector("#summary");
const warningsEl = document.querySelector("#warnings");
const allocationsEl = document.querySelector("#allocations");
const excludedEl = document.querySelector("#excluded");
const remindersEl = document.querySelector("#reminders");
const yieldStripEl = document.querySelector("#yield-strip");
const nextActionsEl = document.querySelector("#next-actions");
const downloadIcsBtn = document.querySelector("#download-ics");
const syncBalancesBtn = document.querySelector("#sync-balances");
const resultsPanelEl = document.querySelector(".results-panel");
const submitPlanBtn = form?.querySelector('button[type="submit"]');
const balanceStatusEl = document.querySelector("#balance-status");
const assetOverviewEl = document.querySelector("#asset-overview");
const presetStatusEl = document.querySelector("#preset-status");
const heroReferenceInputEl = document.querySelector("#hero-reference-input");
const sidebarReferenceInputEl = document.querySelector("#sidebar-reference-input");
const presetButtons = Array.from(document.querySelectorAll(".preset-chip"));
const tgBotTokenEl = document.querySelector("#tg-bot-token");
const tgChatIdEl = document.querySelector("#tg-chat-id");
const tgSaveBtn = document.querySelector("#tg-save");
const tgTestBtn = document.querySelector("#tg-test");
const tgPushBtn = document.querySelector("#tg-push");
const tgDisconnectBtn = document.querySelector("#tg-disconnect");
const tgStatusEl = document.querySelector("#tg-status");
const scenarioStageEl = document.querySelector("#scenario-stage");
const scenarioVisualEl = document.querySelector("#scenario-visual");
const scenarioContentEl = document.querySelector("#scenario-content");
const scenarioDotsEl = document.querySelector("#scenario-dots");
const scenarioPrevBtn = document.querySelector("#scenario-prev");
const scenarioNextBtn = document.querySelector("#scenario-next");
const nowInputEl = form?.elements?.namedItem("now");

let latestIcs = "";
let latestIcsFilename = "bnb-yield-cruiser-reminders.ics";
let telegramState = {
  connected: false,
  enabled: false,
  chat_id: "",
  masked_token: "",
  source: "none"
};
let healthState = {
  live_credentials: false,
};
let currentScenarioIndex = 0;
let scenarioIntervalId = 0;
let plannerRunTimerId = 0;
let plannerRequestSeq = 0;

const bucketMap = {
  "Reserve": "流动性预留",
  "Core Yield": "核心收益",
  "Event Capture": "事件捕捉",
  "Advanced Optional": "高级可选"
};

const modeMap = {
  "sample": "示例数据",
  "auto": "自动选择",
  "live": "实时数据",
  "mixed-public": "示例数据 + 官方公告",
  "mixed-live": "实时收益 + 本地备用事件",
  "live+public": "实时收益 + 官方公告"
};

const riskMap = {
  "low": "低风险",
  "medium": "中风险",
  "high": "高风险"
};

const sourceTypeMap = {
  "official_api": "官方 API",
  "official_announcement": "官方公告",
  "official_rule": "官方规则页",
  "derived_plan": "流动性缓冲",
  "sample_feed": "示例数据",
  "third_party_signal": "第三方信号"
};

const presetMap = {
  "conservative": {
    label: "保守收益",
    description: "优先兼顾流动性、基础收益和官方活动资格。",
    values: {
      bnb: 8,
      usdt: 3000,
      liquidity_window_days: 7,
      risk_tolerance: "low",
      allow_locked_products: true,
      allow_advanced_products: false,
      prefers_bnb_native: true,
      reminder_mode: "deadline_and_24h"
    }
  },
  "event": {
    label: "活动优先",
    description: "更关注官方公告窗口、活动资格和提醒节奏。",
    values: {
      bnb: 16,
      usdt: 1200,
      liquidity_window_days: 14,
      risk_tolerance: "low",
      allow_locked_products: true,
      allow_advanced_products: false,
      prefers_bnb_native: true,
      reminder_mode: "deadline_and_24h"
    }
  },
  "advanced": {
    label: "进阶探索",
    description: "接受部分锁仓和更复杂产品，同时保留一部分流动性。",
    values: {
      bnb: 22,
      usdt: 5000,
      liquidity_window_days: 30,
      risk_tolerance: "medium",
      allow_locked_products: true,
      allow_advanced_products: true,
      prefers_bnb_native: true,
      reminder_mode: "deadline_and_1h"
    }
  }
};

const scenarios = [
  {
    id: "steady",
    eyebrow: "场景 01 / 稳健配置",
    title: "7 天内要保留流动性，同时不想错过 BNB 收益",
    subtitle: "适合大多数已经持有 BNB 的用户。先保留短期可用余额，再把剩余 BNB 配置到官方收益产品，并配合公告提醒。",
    preset: "conservative",
    balances: { BNB: 8, USDT: 3000 },
    liquidityWindowDays: 7,
    riskTolerance: "low",
    reminderMode: "deadline_and_24h",
    focus: "保留流动性 + 获取基础收益",
    badges: ["流动性优先", "基础收益优先", "低打扰"],
    detailCards: [
      { label: "推荐偏好", value: "保守收益" },
      { label: "参考持仓", value: "8 BNB + 3000 USDT" },
      { label: "提醒节奏", value: "24 小时前 + 截止" },
      { label: "执行节奏", value: "日常配置，随用随取" }
    ],
    lanes: [
      { label: "流动性预留", value: 78, tone: "reserve" },
      { label: "核心收益", value: 66, tone: "yield" },
      { label: "事件捕捉", value: 42, tone: "event" }
    ],
    steps: [
      "先划出 7 天内可能要用的 BNB 和 USDT，保证短期调度不受影响。",
      "把剩余 BNB 配置到活期收益产品，优先承接官方原生收益和资格。",
      "只对已确认的公告窗口开提醒，避免被未确认信号误导。"
    ],
    applyNote: "带入后会自动填入 8 BNB、3000 USDT 和 7 天窗口，并重新生成方案。"
  },
  {
    id: "event",
    eyebrow: "场景 02 / 公告关注期",
    title: "重点关注 Launchpool 与 HODLer，不想错过公告窗口",
    subtitle: "把提醒和官方公告确认放到更靠前的位置，接受更长一点的观察周期，但依然不默认自动申购。",
    preset: "event",
    balances: { BNB: 16, USDT: 1200 },
    liquidityWindowDays: 14,
    riskTolerance: "low",
    reminderMode: "deadline_and_24h",
    focus: "公告窗口 + 资格承接",
    badges: ["活动机会优先", "公告跟踪", "提醒联动"],
    detailCards: [
      { label: "推荐偏好", value: "活动优先" },
      { label: "参考持仓", value: "16 BNB + 1200 USDT" },
      { label: "提醒节奏", value: "Telegram + 日历双提醒" },
      { label: "执行节奏", value: "窗口前 24 小时开始关注" }
    ],
    lanes: [
      { label: "流动性预留", value: 52, tone: "reserve" },
      { label: "核心收益", value: 61, tone: "yield" },
      { label: "事件捕捉", value: 91, tone: "event" }
    ],
    steps: [
      "把 BNB 的活动资格层和流动性缓冲拆开，不把全部仓位一次锁死。",
      "公告一旦确认，优先生成 Telegram 和日历提醒，确保不漏掉时间窗口。",
      "结果区重点看“为什么选它”和“资格说明”，确认能否承接活动。"
    ],
    applyNote: "带入后会自动填入 16 BNB、1200 USDT 和 14 天窗口，并重新生成方案。"
  },
  {
    id: "advanced",
    eyebrow: "场景 03 / 进阶配置",
    title: "愿意锁一部分 BNB，争取更多收益叠加机会",
    subtitle: "适合接受中等复杂度的用户。保留一部分现货机动，其余仓位再看锁仓、资格叠加和进阶候选。",
    preset: "advanced",
    balances: { BNB: 22, USDT: 5000 },
    liquidityWindowDays: 30,
    riskTolerance: "medium",
    reminderMode: "deadline_and_1h",
    focus: "锁仓收益 + 进阶机会",
    badges: ["允许锁仓", "可看进阶产品", "仍保留备用金"],
    detailCards: [
      { label: "推荐偏好", value: "进阶探索" },
      { label: "参考持仓", value: "22 BNB + 5000 USDT" },
      { label: "提醒节奏", value: "1 小时前 + 截止" },
      { label: "执行节奏", value: "月度配置，滚动复盘" }
    ],
    lanes: [
      { label: "流动性预留", value: 44, tone: "reserve" },
      { label: "核心收益", value: 74, tone: "yield" },
      { label: "事件捕捉", value: 68, tone: "event" }
    ],
    steps: [
      "先保留一部分可用现货，避免全部资金被锁仓或活动周期占住。",
      "对中长期不用的 BNB，再考虑锁仓与更高阶的收益候选。",
      "把提醒节奏收短到 1 小时前，更适合进阶用户在最后窗口做判断。"
    ],
    applyNote: "带入后会自动填入 22 BNB、5000 USDT 和 30 天窗口，并重新生成方案。"
  }
];

function amountDigits(amount, asset, mode = "default") {
  const abs = Math.abs(Number(amount || 0));
  if (["USDT", "USDC", "FDUSD"].includes(asset)) {
    if (mode === "yield" && abs > 0 && abs < 1) return 4;
    return 2;
  }
  if (mode === "yield") {
    if (abs >= 0.01) return 4;
    if (abs >= 0.0001) return 6;
    return 8;
  }
  return 4;
}

function formatAmount(amount, asset, mode = "default") {
  const numeric = Number(amount || 0);
  const digits = amountDigits(amount, asset, mode);
  const threshold = 1 / (10 ** digits);
  if (mode === "yield" && numeric > 0 && numeric < threshold) {
    return `<${threshold.toLocaleString("zh-CN", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    })} ${asset}>`;
  }
  return `${numeric.toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  })} ${asset}`;
}

function formatApr(item) {
  if (item.apr_type === "event") return "事件机会";
  if (item.apr_type === "n/a") return "流动性缓冲";
  const apr = Number(item.apr_value || 0);
  if (apr <= 0) return "0.00%";
  if (apr >= 1) return `${apr.toFixed(2)}%`;
  if (apr >= 0.1) return `${apr.toFixed(3)}%`;
  if (apr >= 0.01) return `${apr.toFixed(4)}%`;
  if (apr >= 0.001) return `${apr.toFixed(5)}%`;
  return `<0.001%`;
}

function formatBalance(amount, asset) {
  const digits = ["USDT", "USDC", "FDUSD"].includes(asset) ? 2 : 4;
  return Number(amount).toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

function projectedYield(item, days) {
  if (item.apr_type === "event" || item.apr_type === "n/a") return null;
  const amount = Number(item.amount || 0);
  const apr = Number(item.apr_value || 0) / 100;
  return amount * apr * (days / 365);
}

function annualizedYield(item) {
  if (item.apr_type === "event" || item.apr_type === "n/a") return null;
  return Number(item.amount || 0) * (Number(item.apr_value || 0) / 100);
}

function aggregateProjectedYield(items, days) {
  return items.reduce((totals, item) => {
    const value = projectedYield(item, days);
    if (value === null || value <= 0) return totals;
    totals[item.asset] = (totals[item.asset] || 0) + value;
    return totals;
  }, {});
}

function aggregateAnnualizedYield(items) {
  return items.reduce((totals, item) => {
    const value = annualizedYield(item);
    if (value === null || value <= 0) return totals;
    totals[item.asset] = (totals[item.asset] || 0) + value;
    return totals;
  }, {});
}

function yieldSummary(item, days) {
  if (item.apr_type === "event") {
    return {
      title: "收益测算",
      value: "活动机会，不按固定 APR 估算",
      note: "这类配置主要承接空投、Launchpool 或活动资格，不适合直接折算为固定收益。"
    };
  }
  if (item.apr_type === "n/a") {
    return {
      title: "收益测算",
      value: "流动性缓冲，不参与收益估算",
      note: "这部分资金主要用于保留可用余额和短期调度空间。"
    };
  }

  return {
    title: `预计 ${days} 天收益`,
    value: formatAmount(projectedYield(item, days), item.asset, "yield"),
    note: `折算全年约 ${formatAmount(annualizedYield(item), item.asset, "yield")}`
  };
}

function renderYieldStrip(items, days) {
  const projected = aggregateProjectedYield(items, days);
  const annualized = aggregateAnnualizedYield(items);
  const projectedEntries = Object.entries(projected);
  const eventCount = items.filter((item) => item.apr_type === "event").length;
  const fixedCount = items.filter((item) => projectedYield(item, days) !== null).length;

  if (!projectedEntries.length) {
    yieldStripEl.innerHTML = `
      <div class="yield-banner-empty">
        当前配置以流动性预留或活动机会为主，暂时没有固定收益测算结果。
      </div>
    `;
    return;
  }

  const statCards = projectedEntries
    .map(([asset, value]) => {
      const yearly = annualized[asset] || 0;
      return `
        <div class="yield-stat">
          <span>预计 ${days} 天 ${escapeHtml(asset)} 收益</span>
          <strong>${escapeHtml(formatAmount(value, asset, "yield"))}</strong>
          <span>折算全年约 ${escapeHtml(formatAmount(yearly, asset, "yield"))}</span>
        </div>
      `;
    })
    .join("");

  yieldStripEl.innerHTML = `
    <div class="yield-banner">
      <div>
        <div class="yield-banner-label">收益概览</div>
        <h4>预计 ${days} 天固定收益</h4>
        <p>
          当前共测算了 ${fixedCount} 个固定收益仓位；
          ${eventCount ? `另有 ${eventCount} 项活动机会未纳入固定收益测算。` : "当前所有配置均已纳入固定收益测算。"}
        </p>
      </div>
      <div class="yield-stats">${statCards}</div>
    </div>
  `;
}

function warningMeta(text) {
  if (text.includes("未检测到实时 API 凭证")) {
    return {
      level: "info",
      text: "当前展示的是示例数据。接入真实 API 后会自动切到实时收益数据。"
    };
  }
  if (text.includes("实时资产口径已切换为可调度资产")) {
    return {
      level: "info",
      text
    };
  }
  if (text.includes("公告事件回退")) {
    return {
      level: "warning",
      text: text.includes("官方反爬挑战")
        ? "币安公告列表当前触发官方 WAF 挑战，活动机会先使用本地备用事件数据。"
        : "官方公告本次未刷新成功，当前先使用本地备用事件数据。"
    };
  }
  if (text.includes("回退")) {
    return {
      level: "warning",
      text
    };
  }
  return {
    level: "danger",
    text
  };
}

function pill(label, value) {
  return `<span class="summary-pill"><strong>${label}</strong> ${value}</span>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    });
  } catch {
    return value;
  }
}

function localDateTimeValue(date = new Date()) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function timezoneOffsetForValue(value) {
  if (!value) {
    const offsetMinutes = -new Date().getTimezoneOffset();
    const sign = offsetMinutes >= 0 ? "+" : "-";
    const absolute = Math.abs(offsetMinutes);
    return `${sign}${String(Math.floor(absolute / 60)).padStart(2, "0")}:${String(absolute % 60).padStart(2, "0")}`;
  }

  const [datePart = "", timePart = "00:00"] = String(value).split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour, minute] = timePart.split(":").map(Number);
  const localDate = new Date(year, (month || 1) - 1, day || 1, hour || 0, minute || 0, 0);
  const offsetMinutes = -localDate.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const absolute = Math.abs(offsetMinutes);
  return `${sign}${String(Math.floor(absolute / 60)).padStart(2, "0")}:${String(absolute % 60).padStart(2, "0")}`;
}

async function parseJsonResponse(response) {
  const raw = await response.text();
  try {
    return raw ? JSON.parse(raw) : {};
  } catch {
    throw new Error(raw || "服务返回了无法解析的数据。");
  }
}

function formatTelegramSource(source) {
  if (source === "env") return "环境变量";
  if (source === "file") return "本地保存";
  return "未连接";
}

function renderTelegramStatus(status = telegramState, flashText = "", flashLevel = "") {
  telegramState = {
    connected: Boolean(status.connected),
    enabled: Boolean(status.enabled),
    chat_id: status.chat_id || "",
    masked_token: status.masked_token || "",
    source: status.source || "none"
  };

  tgTestBtn.disabled = !telegramState.connected;
  tgPushBtn.disabled = !telegramState.connected;
  tgDisconnectBtn.disabled = !telegramState.connected && telegramState.source !== "env";

  let className = "telegram-status";
  let text = "未连接 Telegram。填写 Bot Token 和 Chat ID 后即可发送测试消息。";

  if (telegramState.connected) {
    className += " is-connected";
    text = `已连接 Telegram（${formatTelegramSource(telegramState.source)}）\nChat ID：${telegramState.chat_id}\nToken：${telegramState.masked_token}`;
  }

  if (flashText) {
    className += flashLevel ? ` is-${flashLevel}` : "";
    text = flashText;
  }

  tgStatusEl.className = className;
  tgStatusEl.textContent = text;
}

function renderBalanceStatus(text, level = "") {
  let className = "balance-status";
  if (level) {
    className += ` is-${level}`;
  }
  balanceStatusEl.className = className;
  balanceStatusEl.textContent = text;
}

function renderAssetOverview(overview = {}) {
  if (!assetOverviewEl) return;

  const assets = Object.values((overview && overview.assets) || {});
  if (!assets.length) {
    assetOverviewEl.innerHTML = "";
    return;
  }

  const cards = assets
    .map((item) => `
      <article class="asset-overview-card">
        <div class="asset-overview-card-head">
          <strong>${escapeHtml(item.asset)}</strong>
          <span>总持仓 ${escapeHtml(formatAmount(item.total || 0, item.asset))}</span>
        </div>
        <div class="asset-overview-metrics">
          <div class="asset-overview-metric">
            <span>现货</span>
            <strong>${escapeHtml(formatAmount(item.spot || 0, item.asset))}</strong>
          </div>
          <div class="asset-overview-metric">
            <span>Earn 活期</span>
            <strong>${escapeHtml(formatAmount(item.simple_earn_flexible || 0, item.asset))}</strong>
          </div>
          <div class="asset-overview-metric">
            <span>已锁仓</span>
            <strong>${escapeHtml(formatAmount(item.simple_earn_locked || 0, item.asset))}</strong>
          </div>
          <div class="asset-overview-metric is-highlight">
            <span>可调度</span>
            <strong>${escapeHtml(formatAmount(item.deployable || 0, item.asset))}</strong>
          </div>
        </div>
      </article>
    `)
    .join("");

  assetOverviewEl.innerHTML = `
    <div class="asset-overview-head">
      <div>
        <span class="asset-overview-kicker">资产口径</span>
        <strong>现货 / Earn 活期 / 已锁仓 / 可调度</strong>
      </div>
      <p>${escapeHtml(overview.scope_note || "默认带入口径为可调度资产。")}</p>
      ${overview.updated_at ? `<p class="asset-overview-updated">更新时间：${escapeHtml(formatDate(overview.updated_at))}</p>` : ""}
    </div>
    <div class="asset-overview-grid">${cards}</div>
  `;
}

function motionEnabled() {
  return !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function replayAnimationClass(element, className) {
  if (!element) return;
  element.classList.remove(className);
  void element.offsetWidth;
  element.classList.add(className);
}

function setResultsLoadingState(isLoading) {
  if (resultsPanelEl) {
    resultsPanelEl.classList.toggle("is-loading", isLoading);
  }
  if (submitPlanBtn) {
    submitPlanBtn.classList.toggle("is-loading", isLoading);
    submitPlanBtn.setAttribute("aria-busy", String(isLoading));
  }
}

function animateNodes(container, selector) {
  if (!container) return;
  const nodes = Array.from(container.querySelectorAll(selector));
  nodes.forEach((node, index) => {
    node.style.setProperty("--stagger-index", index);
    if (!motionEnabled()) {
      node.classList.remove("motion-appear");
      return;
    }
    replayAnimationClass(node, "motion-appear");
  });
}

function animateResultBlocks() {
  animateNodes(yieldStripEl, ".yield-banner, .yield-banner-empty");
  animateNodes(summaryEl, ".summary-pill");
  animateNodes(nextActionsEl, ".next-action-column");
  animateNodes(allocationsEl, ".allocation-card");
  animateNodes(excludedEl, ".list-item");
  animateNodes(remindersEl, ".list-item");
}

function playScenarioTransition() {
  if (!motionEnabled()) return;
  replayAnimationClass(scenarioVisualEl, "is-scene-entering");
  replayAnimationClass(scenarioContentEl, "is-scene-entering");
}

function initEntranceMotion() {
  const targets = [
    document.querySelector(".topbar"),
    document.querySelector(".hero-copy"),
    document.querySelector(".hero-panel"),
    document.querySelector(".scenario-stage"),
    document.querySelector(".planner-panel"),
    document.querySelector(".results-panel")
  ].filter(Boolean);

  targets.forEach((target, index) => {
    target.classList.add("motion-surface");
    target.style.setProperty("--motion-delay", `${index * 70}ms`);
  });

  if (!motionEnabled()) {
    targets.forEach((target) => target.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    {
      threshold: 0.18,
      rootMargin: "0px 0px -8% 0px"
    }
  );

  targets.forEach((target) => observer.observe(target));
}

function setScenarioForPreset(name) {
  const scenarioIndex = scenarios.findIndex((item) => item.preset === name);
  if (scenarioIndex >= 0) {
    showScenario(scenarioIndex);
  }
}

function applyPreset(name, options = {}) {
  const preset = presetMap[name];
  if (!preset) return;
  const {
    syncBalances = true,
    syncScenario = true,
    statusSuffix = ""
  } = options;
  if (syncBalances) {
    form.elements.namedItem("bnb").value = preset.values.bnb;
    form.elements.namedItem("usdt").value = preset.values.usdt;
  }
  form.elements.namedItem("liquidity_window_days").value = preset.values.liquidity_window_days;
  form.elements.namedItem("risk_tolerance").value = preset.values.risk_tolerance;
  form.elements.namedItem("allow_locked_products").checked = preset.values.allow_locked_products;
  form.elements.namedItem("allow_advanced_products").checked = preset.values.allow_advanced_products;
  form.elements.namedItem("prefers_bnb_native").checked = preset.values.prefers_bnb_native;
  form.elements.namedItem("reminder_mode").value = preset.values.reminder_mode;
  presetButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.preset === name);
  });
  if (syncScenario) {
    setScenarioForPreset(name);
  }
  syncPresetStatusFromForm(statusSuffix);
}

function reminderModeText(value) {
  if (value === "deadline_and_24h") return "24 小时前 + 截止";
  if (value === "deadline_and_1h") return "1 小时前 + 截止";
  return "仅截止提醒";
}

function currentScenarioInputs() {
  return {
    bnb: Number(form.elements.namedItem("bnb")?.value || 0),
    usdt: Number(form.elements.namedItem("usdt")?.value || 0),
    liquidityWindowDays: Number(form.elements.namedItem("liquidity_window_days")?.value || 0),
    riskTolerance: String(form.elements.namedItem("risk_tolerance")?.value || "low"),
    reminderMode: String(form.elements.namedItem("reminder_mode")?.value || "deadline"),
    allowLockedProducts: Boolean(form.elements.namedItem("allow_locked_products")?.checked),
    allowAdvancedProducts: Boolean(form.elements.namedItem("allow_advanced_products")?.checked),
    prefersBnbNative: Boolean(form.elements.namedItem("prefers_bnb_native")?.checked)
  };
}

function activePresetName() {
  return presetButtons.find((button) => button.classList.contains("is-active"))?.dataset.preset || "conservative";
}

function syncPresetStatusFromForm(statusSuffix = "") {
  const presetName = activePresetName();
  const preset = presetMap[presetName];
  if (!preset || !presetStatusEl) return;
  const current = currentScenarioInputs();
  const balanceText = `${formatAmount(current.bnb, "BNB")} + ${formatAmount(current.usdt, "USDT")}`;
  const windowText = `${current.liquidityWindowDays} 天 / ${riskMap[current.riskTolerance] || current.riskTolerance}`;
  presetStatusEl.textContent = `当前预设：${preset.label}。当前输入 ${balanceText} / ${windowText}。${preset.description}${statusSuffix}`;
}

function syncReferenceCopyFromForm() {
  const current = currentScenarioInputs();
  const balanceText = `${formatAmount(current.bnb, "BNB")} + ${formatAmount(current.usdt, "USDT")}`;
  const riskText = riskMap[current.riskTolerance] || current.riskTolerance;
  if (heroReferenceInputEl) {
    heroReferenceInputEl.textContent = `${balanceText} / ${current.liquidityWindowDays} 天 / ${riskText}`;
  }
  if (sidebarReferenceInputEl) {
    sidebarReferenceInputEl.textContent = `当前输入：${balanceText} · ${current.liquidityWindowDays} 天 · ${riskText}。`;
  }
}

function scenarioExecutionTempo(days) {
  if (days <= 7) return "短期调度，保持灵活";
  if (days <= 30) return "按周跟进，保留弹性";
  return "按月复盘，偏中长期";
}

function scenarioLaneValues(scenario, current) {
  const laneMap = Object.fromEntries(scenario.lanes.map((lane) => [lane.label, lane.value]));
  let reserve = Number(laneMap["流动性预留"] || 52);
  let core = Number(laneMap["核心收益"] || 64);
  let event = Number(laneMap["事件捕捉"] || 56);

  if (current.liquidityWindowDays <= 7) reserve += 8;
  else if (current.liquidityWindowDays <= 14) reserve += 2;
  else if (current.liquidityWindowDays <= 30) reserve -= 4;
  else if (current.liquidityWindowDays <= 60) reserve -= 10;
  else reserve -= 14;

  if (current.riskTolerance === "low") reserve += 3;
  if (current.riskTolerance === "high") reserve -= 8;
  if (!current.allowLockedProducts) reserve += 4;

  if (current.allowLockedProducts && current.liquidityWindowDays >= 30) core += 6;
  if (!current.allowLockedProducts) core -= 4;
  if (current.riskTolerance === "high") core += 4;
  if (current.riskTolerance === "low") core += 2;

  if (current.prefersBnbNative) event += 4;
  if (current.reminderMode === "deadline_and_1h") event += 3;
  if (current.reminderMode === "deadline") event -= 4;
  if (current.allowAdvancedProducts) event += 4;
  if (current.liquidityWindowDays >= 45) event -= 4;

  return scenario.lanes.map((lane) => {
    let value = lane.value;
    if (lane.label === "流动性预留") value = reserve;
    if (lane.label === "核心收益") value = core;
    if (lane.label === "事件捕捉") value = event;
    return {
      ...lane,
      value: Math.max(24, Math.min(92, Math.round(value)))
    };
  });
}

function scenarioDetailCards(scenario, current) {
  return [
    { label: "当前预设", value: presetMap[scenario.preset]?.label || "未命名预设" },
    { label: "当前持仓", value: `${formatAmount(current.bnb, "BNB")} + ${formatAmount(current.usdt, "USDT")}` },
    { label: "提醒节奏", value: reminderModeText(current.reminderMode) },
    { label: "执行节奏", value: scenarioExecutionTempo(current.liquidityWindowDays) }
  ];
}

function scenarioSteps(scenario, current) {
  if (scenario.id === "event") {
    return [
      `把 BNB 的活动资格层和流动性缓冲拆开，先围绕 ${current.liquidityWindowDays} 天窗口安排仓位。`,
      `公告一旦确认，优先生成 ${reminderModeText(current.reminderMode)} 的 Telegram 和日历提醒。`,
      `结果区重点看“为什么选它”和“资格说明”，确认当前 ${formatAmount(current.bnb, "BNB")} 是否适合承接活动。`
    ];
  }

  if (scenario.id === "advanced") {
    return [
      `先保留一部分可用现货，避免 ${current.liquidityWindowDays} 天内的调度空间被全部锁住。`,
      `对中长期不用的 BNB，再考虑锁仓与更高阶的收益候选。当前风险偏好为 ${riskMap[current.riskTolerance] || current.riskTolerance}。`,
      `把提醒节奏调整为 ${reminderModeText(current.reminderMode)}，更适合在临近窗口时做判断。`
    ];
  }

  return [
    `先划出 ${current.liquidityWindowDays} 天内可能要用的 BNB 和 USDT，保证短期调度不受影响。`,
    `把剩余 BNB 配置到活期收益产品，优先承接官方原生收益和资格。当前输入为 ${formatAmount(current.bnb, "BNB")}。`,
    `只对已确认的公告窗口开提醒，当前提醒节奏为 ${reminderModeText(current.reminderMode)}。`
  ];
}

function scenarioNarrative(scenario, current) {
  const riskText = riskMap[current.riskTolerance] || current.riskTolerance;
  const balanceText = `${formatAmount(current.bnb, "BNB")} + ${formatAmount(current.usdt, "USDT")}`;
  const windowText = `${current.liquidityWindowDays} 天`;
  const nativeBadge = current.prefersBnbNative ? "BNB 原生机会优先" : "基础收益优先";
  const advancedBadge = current.allowAdvancedProducts ? "进阶候选已开启" : "仅看基础方案";
  const lockedBadge = current.allowLockedProducts ? "允许锁仓" : "先不锁仓";

  if (scenario.id === "event") {
    return {
      title: `围绕 ${windowText} 的公告窗口管理 ${formatAmount(current.bnb, "BNB")} 资格仓位`,
      subtitle: `当前输入为 ${balanceText}，风险偏好 ${riskText}。重点把公告确认、提醒节奏和资格承接放在前面，不默认自动申购。`,
      badges: [`${windowText} 窗口`, riskText, "公告机会优先"],
      focus: `公告窗口 + ${riskText} 过滤`,
      applyNote: `会按你当前输入的 ${balanceText}、${windowText} 和 ${riskText} 重新生成方案。`
    };
  }

  if (scenario.id === "advanced") {
    return {
      title: `为 ${formatAmount(current.bnb, "BNB")} 预留机动仓，再筛选锁仓与进阶收益`,
      subtitle: `当前输入为 ${balanceText}，流动性窗口 ${windowText}，风险偏好 ${riskText}。适合把一部分仓位用于锁仓候选，但仍保留可调度资金。`,
      badges: [lockedBadge, riskText, advancedBadge],
      focus: `${lockedBadge} + 进阶收益`,
      applyNote: `会按你当前输入的 ${balanceText}、${windowText} 和 ${riskText} 重新生成方案。`
    };
  }

  return {
    title: `先保留 ${windowText} 流动性，再为 ${formatAmount(current.bnb, "BNB")} 配基础收益`,
    subtitle: `当前输入为 ${balanceText}，风险偏好 ${riskText}。先留出短期可用仓位，再用剩余 BNB 和 USDT 承接官方原生收益。`,
    badges: [`${windowText} 流动性优先`, riskText, nativeBadge],
    focus: `保留流动性 + ${nativeBadge}`,
    applyNote: `会按你当前输入的 ${balanceText}、${windowText} 和 ${riskText} 重新生成方案。`
  };
}

function syncScenarioStageFromForm() {
  if (!scenarioVisualEl || !scenarioContentEl) return;
  renderScenarioStage();
  syncPresetStatusFromForm();
  syncReferenceCopyFromForm();
}

function scenarioCounter(index) {
  return `${String(index + 1).padStart(2, "0")} / ${String(scenarios.length).padStart(2, "0")}`;
}

function renderScenarioStage() {
  if (!scenarioVisualEl || !scenarioContentEl || !scenarioDotsEl || !scenarios.length) return;

  const scenario = scenarios[currentScenarioIndex];
  const current = currentScenarioInputs();
  const lanes = scenarioLaneValues(scenario, current);
  const detailCards = scenarioDetailCards(scenario, current);
  const steps = scenarioSteps(scenario, current);
  const narrative = scenarioNarrative(scenario, current);
  scenarioVisualEl.innerHTML = `
    <div class="scenario-visual-head">
      <div>
        <div class="scenario-kicker">${escapeHtml(scenario.eyebrow)}</div>
        <h4>${escapeHtml(narrative.focus)}</h4>
      </div>
      <div class="scenario-counter">${escapeHtml(scenarioCounter(currentScenarioIndex))}</div>
    </div>
    <div class="scenario-asset-grid">
      <div class="scenario-asset-card">
        <span>当前 BNB</span>
        <strong>${escapeHtml(formatAmount(current.bnb, "BNB"))}</strong>
      </div>
      <div class="scenario-asset-card">
        <span>当前 USDT</span>
        <strong>${escapeHtml(formatAmount(current.usdt, "USDT"))}</strong>
      </div>
      <div class="scenario-asset-card">
        <span>当前流动性窗口</span>
        <strong>${current.liquidityWindowDays} 天</strong>
      </div>
      <div class="scenario-asset-card">
        <span>当前风险偏好</span>
        <strong>${escapeHtml(riskMap[current.riskTolerance] || current.riskTolerance)}</strong>
      </div>
    </div>
    <div class="scenario-lanes">
      ${lanes
        .map(
          (lane) => `
            <div class="scenario-lane">
              <div class="scenario-lane-head">
                <span>${escapeHtml(lane.label)}</span>
                <strong>${lane.value}%</strong>
              </div>
              <div class="scenario-track ${escapeHtml(lane.tone)}" style="--fill:${lane.value}%">
                <span></span>
              </div>
            </div>
          `
        )
        .join("")}
    </div>
    <div class="scenario-route-card">
      ${steps
        .map(
          (step, index) => `
            <div class="scenario-route-row">
              <span>${index + 1}</span>
              <p>${escapeHtml(step)}</p>
            </div>
          `
        )
        .join("")}
    </div>
  `;

  scenarioContentEl.innerHTML = `
    <div class="scenario-content-head">
      <p class="panel-tag">配置思路</p>
      <h3>${escapeHtml(narrative.title)}</h3>
      <p>${escapeHtml(narrative.subtitle)}</p>
    </div>
    <div class="scenario-badge-row">
      ${narrative.badges.map((badge) => `<span class="scenario-badge">${escapeHtml(badge)}</span>`).join("")}
    </div>
    <div class="scenario-detail-grid">
      ${detailCards
        .map(
          (item) => `
            <article class="scenario-detail-card">
              <span>${escapeHtml(item.label)}</span>
              <strong>${escapeHtml(item.value)}</strong>
            </article>
          `
        )
        .join("")}
    </div>
    <div class="scenario-decision-strip">
      <div class="scenario-decision-card">
        <span>场景重点</span>
        <strong>${escapeHtml(narrative.focus)}</strong>
      </div>
      <div class="scenario-decision-card">
        <span>提醒策略</span>
        <strong>${escapeHtml(reminderModeText(current.reminderMode))}</strong>
      </div>
    </div>
    <div class="scenario-actions">
      <button class="primary-button" type="button" data-scenario-apply="${escapeHtml(scenario.id)}">带入当前场景</button>
      <div class="scenario-action-note">${escapeHtml(narrative.applyNote)}</div>
    </div>
  `;

  scenarioDotsEl.innerHTML = scenarios
    .map(
      (item, index) => `
        <button
          class="scenario-dot ${index === currentScenarioIndex ? "is-active" : ""}"
          type="button"
          data-scenario-index="${index}"
          aria-label="切换到${escapeHtml(item.eyebrow)}"
        ></button>
      `
    )
    .join("");

  playScenarioTransition();
}

function stopScenarioRotation() {
  if (scenarioIntervalId) {
    window.clearInterval(scenarioIntervalId);
    scenarioIntervalId = 0;
  }
}

function startScenarioRotation() {
  stopScenarioRotation();
}

function showScenario(index) {
  currentScenarioIndex = (index + scenarios.length) % scenarios.length;
  renderScenarioStage();
}

function applyScenarioById(id) {
  const scenario = scenarios.find((item) => item.id === id);
  if (!scenario) return;
  applyPreset(scenario.preset, {
    syncBalances: true,
    syncScenario: false,
    statusSuffix: ` 已带入场景：${scenario.title}`
  });
  form.elements.namedItem("bnb").value = scenario.balances.BNB;
  form.elements.namedItem("usdt").value = scenario.balances.USDT;
  form.elements.namedItem("liquidity_window_days").value = scenario.liquidityWindowDays;
  form.elements.namedItem("risk_tolerance").value = scenario.riskTolerance;
  form.elements.namedItem("reminder_mode").value = scenario.reminderMode;
  syncScenarioStageFromForm();
  runPlanner().catch((error) => {
    summaryEl.innerHTML = pill("状态", "请求失败");
    renderWarnings([error.message || "带入场景后重新生成失败。"]);
  });
}

function fillSpotBalances(balances) {
  form.elements.namedItem("bnb").value = balances.BNB ?? 0;
  form.elements.namedItem("usdt").value = balances.USDT ?? 0;
  syncScenarioStageFromForm();
}

async function telegramRequest(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const body = await parseJsonResponse(response);
  if (!response.ok || !body.ok) {
    throw new Error(body.error || "Telegram 请求失败。");
  }
  return body;
}

function renderWarnings(warnings) {
  if (!warnings.length) {
    warningsEl.innerHTML = "";
    return;
  }
  warningsEl.innerHTML = warnings
    .map((warning) => {
      const meta = warningMeta(warning);
      return `<div class="message message-${meta.level}">${escapeHtml(meta.text)}</div>`;
    })
    .join("");
}

function actionLink(label, url, extraClass = "") {
  if (!url) return "";
  const className = `action-link${extraClass ? ` ${extraClass}` : ""}`;
  return `<a class="${className}" href="${url}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`;
}

function buildImmediateActions(items) {
  return items
    .filter((item) => item.bucket !== "Event Capture")
    .map((item, index) => {
      if (item.bucket === "Reserve") {
        return {
          order: index + 1,
          title: `保留 ${formatAmount(item.amount, item.asset)} 在现货`,
          detail: `这部分资金主要用于保留短期流动性，当前不建议继续配置到收益产品。`,
          linkLabel: "",
          linkUrl: item.source_url || ""
        };
      }

      if (item.bucket === "Advanced Optional") {
        return {
          order: index + 1,
          title: `按需配置 ${formatAmount(item.amount, item.asset)} 到 ${item.product_name}`,
          detail: `这部分属于进阶候选，只有在你接受更复杂产品时再执行。`,
          linkLabel: item.action_label || "查看详情",
          linkUrl: item.action_url || item.source_url || ""
        };
      }

      return {
        order: index + 1,
        title: `配置 ${formatAmount(item.amount, item.asset)} 到 ${item.product_name}`,
        detail: item.fit || "这是当前方案里建议优先执行的收益配置。",
        linkLabel: item.action_label || "查看详情",
        linkUrl: item.action_url || item.source_url || ""
      };
    });
}

function buildWatchActions(items, reminders) {
  const eventActions = items
    .filter((item) => item.bucket === "Event Capture")
    .map((item) => ({
      title: `关注 ${item.product_name}`,
      detail: item.note || item.fit || "这部分更适合先看公告和时间窗口，再决定是否参与。",
      linkLabel: item.action_label || "查看详情",
      linkUrl: item.action_url || item.source_url || ""
    }));

  const reminderActions = reminders.map((item) => ({
    title: item.title,
    detail: `提醒时间：${formatDate(item.when)}`,
    linkLabel: item.source_url ? "查看来源" : "",
    linkUrl: item.source_url || ""
  }));

  return [...eventActions, ...reminderActions];
}

function buildSkippedActions(items) {
  return items.slice(0, 3).map((item) => ({
    title: item.product_name,
    detail: item.reason || "当前条件下暂不建议纳入。",
    linkLabel: item.source_url ? "查看来源" : "",
    linkUrl: item.source_url || ""
  }));
}

function renderActionColumn(title, note, items, emptyText, tone, tag) {
  const toneBreathClass = tone === "now" ? "breathe-amber" : "";
  const body = items.length
    ? items
        .map(
          (item) => `
            <article class="next-action-item">
              <div class="next-action-title-row">
                ${item.order ? `<span class="next-action-order">${String(item.order).padStart(2, "0")}</span>` : ""}
                <strong>${escapeHtml(item.title)}</strong>
              </div>
              <p>${escapeHtml(item.detail)}</p>
              ${item.linkUrl ? `<div class="next-action-links">${actionLink(item.linkLabel || "查看详情", item.linkUrl)}</div>` : ""}
            </article>
          `
        )
        .join("")
    : `<div class="status-empty">${emptyText}</div>`;

  return `
    <section class="next-action-column tone-${escapeHtml(tone)}">
      <div class="next-action-head">
        <span class="next-action-tag ${toneBreathClass}">${escapeHtml(tag)}</span>
        <h4>${escapeHtml(title)}</h4>
        <p>${escapeHtml(note)}</p>
      </div>
      <div class="next-action-list">${body}</div>
    </section>
  `;
}

function renderNextActions(payload) {
  if (!nextActionsEl) return;
  const allocations = payload.allocations || [];
  const reminders = payload.reminders || [];
  const excluded = payload.excluded || [];

  if (!allocations.length && !reminders.length && !excluded.length) {
    nextActionsEl.innerHTML = "";
    return;
  }

  const immediateActions = buildImmediateActions(allocations);
  const watchActions = buildWatchActions(allocations, reminders);
  const skippedActions = buildSkippedActions(excluded);

  nextActionsEl.innerHTML = `
    <div class="next-actions-panel">
      <div class="next-actions-summary">
        <p class="panel-tag">下一步行动</p>
        <h3>生成方案后，按这个顺序处理</h3>
        <p>先执行可以立刻处理的配置，再把活动型机会交给提醒，最后再看当前不建议纳入的项目。</p>
      </div>
      <div class="next-actions-grid">
        ${renderActionColumn("现在处理", "可以立刻执行或确认的部分。", immediateActions, "当前没有需要立刻处理的配置。", "now", "优先执行")}
        ${renderActionColumn("等待提醒", "活动机会和时间窗口交给提醒来跟进。", watchActions, "当前没有需要等待的提醒事项。", "watch", "等待窗口")}
        ${renderActionColumn("暂不纳入", "当前条件下不建议优先处理的项目。", skippedActions, "当前没有被明确排除的项目。", "skip", "暂缓处理")}
      </div>
    </div>
  `;
}

function renderAllocations(items, days) {
  if (!items.length) {
    allocationsEl.innerHTML = `<div class="status-empty">当前没有可展示的配置结果。</div>`;
    return;
  }

  allocationsEl.innerHTML = items
    .map(
      (item) => {
        const yieldInfo = yieldSummary(item, days);
        return `
        <article class="allocation-card">
          <header>
            <div>
              <div class="tag-row">
                <div class="tag">${escapeHtml(bucketMap[item.bucket] || item.bucket)}</div>
                <div class="meta-tag">${escapeHtml(sourceTypeMap[item.source_type] || item.source_type || "未分类")}</div>
              </div>
              <h3>${escapeHtml(item.product_name)}</h3>
            </div>
            <div class="amount">${escapeHtml(formatAmount(item.amount, item.asset))}</div>
          </header>
          <div class="card-metrics">
            <span class="metric-chip">资产 ${escapeHtml(item.asset)}</span>
            <span class="metric-chip">APR ${escapeHtml(formatApr(item))}</span>
            <span class="metric-chip">锁仓 ${Number(item.lock_days || 0)} 天</span>
            <span class="metric-chip">${escapeHtml(item.liquidity_label || "流动性未分类")}</span>
            <span class="metric-chip">${escapeHtml(item.risk_label || "风险层未分类")}</span>
            <span class="metric-chip">置信度 ${(Number(item.confidence || 0) * 100).toFixed(0)}%</span>
          </div>
          <div class="card-block">
            <div class="card-block-label">为什么选它</div>
            <p>${escapeHtml(item.fit)}</p>
          </div>
          <div class="card-block">
            <div class="card-block-label">补充说明</div>
            <p>${escapeHtml(item.note || "当前没有额外说明。")}</p>
          </div>
          <div class="card-block">
            <div class="card-block-label">资格与限制</div>
            <p>${escapeHtml(item.eligibility_note || "无额外资格说明。")}</p>
          </div>
          <div class="card-block">
            <div class="card-block-label">${escapeHtml(yieldInfo.title)}</div>
            <div class="yield-figure">${escapeHtml(yieldInfo.value)}</div>
            <p class="yield-note">${escapeHtml(yieldInfo.note)}</p>
          </div>
          ${item.action_url ? `<div class="card-block"><a class="action-link" href="${item.action_url}" target="_blank" rel="noreferrer">${escapeHtml(item.action_label || "查看详情")}</a></div>` : ""}
          ${item.source_url ? `<div class="card-block"><a href="${item.source_url}" target="_blank" rel="noreferrer">查看来源</a></div>` : ""}
        </article>
      `;
      }
    )
    .join("");
}

function renderList(target, items, emptyText, renderItem) {
  if (!items.length) {
    target.innerHTML = `<div class="status-empty">${emptyText}</div>`;
    return;
  }
  target.innerHTML = items.map(renderItem).join("");
}

function formPayload() {
  const data = new FormData(form);
  const nowValue = String(data.get("now") || "");
  return {
    mode: data.get("mode"),
    use_wallet_balances: data.get("use_wallet_balances") === "on",
    skip_public_events: data.get("skip_public_events") === "on",
    profile: {
      balances: {
        BNB: Number(data.get("bnb") || 0),
        USDT: Number(data.get("usdt") || 0)
      },
      liquidity_window_days: Number(data.get("liquidity_window_days") || 7),
      risk_tolerance: data.get("risk_tolerance"),
      allow_locked_products: data.get("allow_locked_products") === "on",
      allow_advanced_products: data.get("allow_advanced_products") === "on",
      wants_reminders: data.get("wants_reminders") === "on",
      reminder_mode: data.get("reminder_mode"),
      prefers_bnb_native: data.get("prefers_bnb_native") === "on",
      now: `${nowValue}:00${timezoneOffsetForValue(nowValue)}`
    }
  };
}

function rerunPlannerWithFeedback(message) {
  window.clearTimeout(plannerRunTimerId);
  plannerRunTimerId = window.setTimeout(() => {
    runPlanner().catch((error) => {
      summaryEl.innerHTML = pill("状态", "请求失败");
      renderWarnings([error.message || message]);
    });
  }, 260);
}

async function runPlanner() {
  window.clearTimeout(plannerRunTimerId);
  plannerRunTimerId = 0;
  const requestSeq = ++plannerRequestSeq;
  downloadIcsBtn.disabled = true;
  summaryEl.innerHTML = pill("状态", "生成中...");
  warningsEl.innerHTML = "";
  setResultsLoadingState(true);

  try {
    const response = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload())
    });
    const payload = await parseJsonResponse(response);
    if (requestSeq !== plannerRequestSeq) {
      return;
    }

    if (!response.ok || !payload.ok) {
      summaryEl.innerHTML = pill("状态", "请求失败");
      renderWarnings([payload.error || "方案生成失败，请稍后重试。"]);
      yieldStripEl.innerHTML = "";
      nextActionsEl.innerHTML = "";
      allocationsEl.innerHTML = "";
      excludedEl.innerHTML = "";
      remindersEl.innerHTML = "";
      latestIcs = "";
      return;
    }

    latestIcs = payload.ics_content || "";
    latestIcsFilename = payload.ics_filename || latestIcsFilename;
    downloadIcsBtn.disabled = !latestIcs;
    if (payload.telegram) {
      renderTelegramStatus(payload.telegram);
    }
    const hasLiveAssetOverview = Object.keys((payload.asset_overview && payload.asset_overview.assets) || {}).length > 0;
    if (hasLiveAssetOverview) {
      renderAssetOverview(payload.asset_overview);
    } else if (!healthState.live_credentials) {
      renderAssetOverview({});
    }

    const summaryPills = [
      pill("数据模式", modeMap[payload.data_mode] || payload.data_mode),
      pill("风险偏好", riskMap[payload.profile.risk_tolerance] || payload.profile.risk_tolerance),
      pill("流动性窗口", `${payload.profile.liquidity_window_days} 天`),
      pill("BNB", formatBalance(payload.profile.balances.BNB, "BNB")),
      pill("USDT", formatBalance(payload.profile.balances.USDT, "USDT"))
    ];
    if (payload.asset_overview?.updated_at) {
      summaryPills.push(pill("更新于", formatDate(payload.asset_overview.updated_at)));
    }
    summaryEl.innerHTML = summaryPills.join("");

    renderYieldStrip(payload.allocations || [], payload.profile.liquidity_window_days);
    renderWarnings(payload.warnings || []);
    renderNextActions(payload);
    renderAllocations(payload.allocations || [], payload.profile.liquidity_window_days);

    renderList(
      excludedEl,
      payload.excluded || [],
      "当前没有需要额外说明的未纳入项。",
      (item) => `
        <article class="list-item">
          <strong>${escapeHtml(item.product_name)}</strong>
          <div class="list-meta">
            <span class="tag">${escapeHtml(item.asset)}</span>
            <span class="meta-tag">匹配度 ${Number(item.score).toFixed(2)}</span>
            <span class="meta-tag">${escapeHtml(sourceTypeMap[item.source_type] || item.source_type || "未分类")}</span>
          </div>
          <div class="card-block">
            <div class="list-label">未纳入原因</div>
            <p>${escapeHtml(item.reason)}</p>
          </div>
          ${item.source_url ? `<p><a href="${item.source_url}" target="_blank" rel="noreferrer">查看来源</a></p>` : ""}
        </article>
      `
    );

    renderList(
      remindersEl,
      payload.reminders || [],
      "当前没有提醒安排。",
      (item) => `
        <article class="list-item">
          <strong>${escapeHtml(item.title)}</strong>
          <div class="list-inline">
            <span class="meta-tag">提醒时间 ${escapeHtml(formatDate(item.when))}</span>
          </div>
          <div class="card-block">
            <div class="list-label">提醒内容</div>
            <p>${escapeHtml(item.description)}</p>
          </div>
          ${item.source_url ? `<p><a href="${item.source_url}" target="_blank" rel="noreferrer">查看来源</a></p>` : ""}
        </article>
      `
    );

    animateResultBlocks();
  } catch (error) {
    if (requestSeq !== plannerRequestSeq) {
      return;
    }
    throw error;
  } finally {
    if (requestSeq === plannerRequestSeq) {
      setResultsLoadingState(false);
    }
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await runPlanner();
  } catch (error) {
    summaryEl.innerHTML = pill("状态", "请求失败");
    renderWarnings([error.message || "页面发生意外错误。"]);
  }
});

form.addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  if (!target.matches("input[name], select[name]")) return;
  syncScenarioStageFromForm();
  rerunPlannerWithFeedback("参数更新后重新生成失败。");
});

form.addEventListener("input", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  if (!target.matches("input[name], select[name]")) return;
  syncScenarioStageFromForm();
});

downloadIcsBtn.addEventListener("click", () => {
  if (!latestIcs) return;
  const blob = new Blob([latestIcs], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = latestIcsFilename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
});

tgSaveBtn.addEventListener("click", async () => {
  try {
    const payload = await telegramRequest("/api/telegram/connect", {
      bot_token: tgBotTokenEl.value,
      chat_id: tgChatIdEl.value,
      enabled: true
    });
    tgBotTokenEl.value = "";
    renderTelegramStatus(payload.telegram, "Telegram 已连接，可直接发送测试消息或推送当前方案。", "connected");
  } catch (error) {
    renderTelegramStatus(telegramState, error.message || "Telegram 连接失败。", "danger");
  }
});

tgTestBtn.addEventListener("click", async () => {
  try {
    const payload = await telegramRequest("/api/telegram/test");
    renderTelegramStatus(payload.telegram, payload.message || "测试消息已发送。", "connected");
  } catch (error) {
    renderTelegramStatus(telegramState, error.message || "测试消息发送失败。", "danger");
  }
});

tgPushBtn.addEventListener("click", async () => {
  try {
    const payload = await telegramRequest("/api/telegram/push-plan", formPayload());
    renderTelegramStatus(payload.telegram, payload.message || "当前方案已发送到 Telegram。", "connected");
  } catch (error) {
    renderTelegramStatus(telegramState, error.message || "收益方案推送失败。", "danger");
  }
});

tgDisconnectBtn.addEventListener("click", async () => {
  try {
    const payload = await telegramRequest("/api/telegram/disconnect");
    tgBotTokenEl.value = "";
    tgChatIdEl.value = "";
    renderTelegramStatus(payload.telegram, payload.message || "Telegram 连接已断开。", "warning");
  } catch (error) {
    renderTelegramStatus(telegramState, error.message || "断开 Telegram 连接失败。", "danger");
  }
});

syncBalancesBtn.addEventListener("click", async () => {
  try {
    renderBalanceStatus("正在读取资产概览...", "warning");
    const response = await fetch("/api/binance/asset-overview");
    const payload = await parseJsonResponse(response);
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "资产概览读取失败。");
    }
    renderAssetOverview(payload.asset_overview || {});
    fillSpotBalances(payload.balances || {});
    if (form.elements.namedItem("mode")?.value === "sample") {
      form.elements.namedItem("mode").value = "auto";
    }
    renderBalanceStatus(
      `已读取可调度资产：BNB ${formatBalance(payload.balances.BNB || 0, "BNB")} / USDT ${formatBalance(payload.balances.USDT || 0, "USDT")}。口径 = 现货 + 可赎回 Earn 活期；已锁仓仅展示，不自动带入，并已切到自动选择模式。${payload.updated_at ? ` 更新时间：${formatDate(payload.updated_at)}。` : ""}`,
      "connected"
    );
    rerunPlannerWithFeedback("资产概览同步后重新生成失败。");
  } catch (error) {
    renderBalanceStatus(error.message || "资产概览读取失败。", "danger");
  }
});

applyPreset("conservative");
initEntranceMotion();

if (nowInputEl && !nowInputEl.value) {
  nowInputEl.value = localDateTimeValue();
}

if (scenarioPrevBtn && scenarioNextBtn && scenarioDotsEl && scenarioContentEl && scenarioStageEl) {
  scenarioPrevBtn.addEventListener("click", () => {
    showScenario(currentScenarioIndex - 1);
  });

  scenarioNextBtn.addEventListener("click", () => {
    showScenario(currentScenarioIndex + 1);
  });

  scenarioDotsEl.addEventListener("click", (event) => {
    const button = event.target.closest("[data-scenario-index]");
    if (!button) return;
    showScenario(Number(button.dataset.scenarioIndex));
  });

  scenarioContentEl.addEventListener("click", (event) => {
    const button = event.target.closest("[data-scenario-apply]");
    if (!button) return;
    applyScenarioById(button.dataset.scenarioApply);
  });

  showScenario(0);
}

runPlanner().catch((error) => {
  summaryEl.innerHTML = pill("状态", "请求失败");
  renderWarnings([error.message || "页面初始化失败。"]);
  yieldStripEl.innerHTML = "";
});

fetch("/api/telegram/status")
  .then((response) => parseJsonResponse(response))
  .then((payload) => {
    if (payload.ok && payload.telegram) {
      renderTelegramStatus(payload.telegram);
    }
  })
  .catch(() => {
    renderTelegramStatus(telegramState, "Telegram 状态读取失败，稍后可重新尝试。", "warning");
  });

fetch("/api/health")
  .then((response) => parseJsonResponse(response))
  .then((payload) => {
    healthState.live_credentials = Boolean(payload.live_credentials);
    syncBalancesBtn.disabled = !healthState.live_credentials;
    if (healthState.live_credentials) {
      renderBalanceStatus("已检测到实时 API 凭证。可以读取现货、Earn 活期和已锁仓概览；默认带入口径为可调度资产。", "connected");
      return;
    }
    renderAssetOverview({});
    renderBalanceStatus("当前未检测到实时 API 凭证，先使用手动输入。接入后可读取资产概览。", "warning");
  })
  .catch(() => {
    syncBalancesBtn.disabled = true;
    renderAssetOverview({});
    renderBalanceStatus("实时 API 状态读取失败，当前先使用手动输入。", "warning");
  });

presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    applyPreset(button.dataset.preset);
    rerunPlannerWithFeedback("预设切换后重新生成失败。");
  });
});
