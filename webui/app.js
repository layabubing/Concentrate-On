const PERSONALIZATION_KEY = "concentrateon.personalization";
const VALID_THEME_MODES = ["light", "dark"];
const VALID_COLOR_SCHEMES = ["blue", "green", "red", "yellow"];
const VALID_PAGES = ["focus", "tasks", "stats", "settings"];

function normalizeDomainInput(value) {
  let cleaned = String(value || "").trim().toLowerCase();
  if (!cleaned) {
    return "";
  }
  if (cleaned.includes("://")) {
    cleaned = cleaned.split("://", 2)[1];
  }
  cleaned = cleaned.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0];
  cleaned = cleaned.split("@").pop();
  cleaned = cleaned.replace(/^\*\./, "").replace(/^www\./, "").replace(/^\.+|\.+$/g, "");
  if (cleaned.includes(":")) {
    const parts = cleaned.split(":");
    const maybePort = parts[parts.length - 1];
    if (/^\d+$/.test(maybePort)) {
      cleaned = parts.slice(0, -1).join(":");
    }
  }
  if (!cleaned || /\s/.test(cleaned)) {
    return "";
  }

  const labels = cleaned.split(".");
  const valid = labels.length > 1 && labels.every((label) => (
    label.length > 0
    && /^[a-z0-9-]+$/.test(label)
    && !label.startsWith("-")
    && !label.endsWith("-")
  ));
  return valid ? cleaned : "";
}

function readPersonalization() {
  try {
    return JSON.parse(window.localStorage.getItem(PERSONALIZATION_KEY) || "{}");
  } catch {
    return {};
  }
}

const storedPersonalization = readPersonalization();
const storedThemeMode = VALID_THEME_MODES.includes(storedPersonalization.themeMode) ? storedPersonalization.themeMode : "light";
const storedColorScheme = VALID_COLOR_SCHEMES.includes(storedPersonalization.colorScheme) ? storedPersonalization.colorScheme : "blue";
const storedActivePage = VALID_PAGES.includes(storedPersonalization.activePage) ? storedPersonalization.activePage : "focus";

const app = Vue.createApp({
  components: {
    FocusPage: window.FocusPage,
    TasksPage: window.TasksPage,
    StatsPage: window.StatsPage,
    SettingsPage: window.SettingsPage,
  },
  data() {
    return {
      snapshot: {
        settings: {
          blocked_domains: [],
          session_minutes: 45,
          pomodoro_minutes: 25,
          short_break_minutes: 5,
          long_break_minutes: 15,
          long_break_every: 4,
          theme_mode: "light",
          color_scheme: "blue",
          daily_quote_enabled: true,
        },
        current_session: null,
        tasks: [],
        pomodoro: {
          completed: 0,
          next_break_type: "short_break",
        },
        stats: {
          total_sessions: 0,
          total_focus_seconds: 0,
          today_sessions: 0,
          today_focus_seconds: 0,
        },
        recent_sessions: [],
        blocker: {
          is_admin: false,
          hosts_path: "",
          block_ip: "0.0.0.0",
          active_domains: [],
          elevation_supported: false,
        },
      },
      navItems: [
        { key: "focus", label: "专注", icon: "◐" },
        { key: "tasks", label: "任务", icon: "□" },
        { key: "stats", label: "统计", icon: "▦" },
        { key: "settings", label: "设置", icon: "◎" },
      ],
      activePage: storedActivePage,
      selectedTaskIds: [],
      newTaskTitle: "",
      taskMessage: "",
      taskSubmitting: false,
      form: {
        sessionMinutes: 45,
        pomodoroMinutes: 25,
        shortBreakMinutes: 5,
        longBreakMinutes: 15,
        longBreakEvery: 4,
        blockedDomains: [],
        newBlockedDomain: "",
        themeMode: storedThemeMode,
        colorScheme: storedColorScheme,
        dailyQuoteEnabled: true,
      },
      themeOptions: [
        { value: "light", label: "浅色" },
        { value: "dark", label: "深色" },
      ],
      colorOptions: [
        { value: "blue", label: "淡蓝" },
        { value: "green", label: "淡绿" },
        { value: "red", label: "淡红" },
        { value: "yellow", label: "淡黄" },
      ],
      settingsDirty: false,
      submitting: false,
      settingsSubmitting: false,
      settingsSaveStatus: "saved",
      syncing: false,
      apiOnline: false,
      lastSyncAt: "",
      lastApiError: "",
      elevationRequesting: false,
      elevationMessage: "",
      dailyQuote: "",
      dailyQuoteLoading: false,
      dailyQuoteError: "",
      localElapsed: 0,
      refreshTimer: null,
      tickTimer: null,
      settingsSaveTimer: null,
    };
  },

  computed: {
    settings() {
      return this.snapshot.settings;
    },

    stats() {
      return this.snapshot.stats;
    },

    blocker() {
      return this.snapshot.blocker;
    },

    currentSession() {
      return this.snapshot.current_session;
    },

    tasks() {
      return this.snapshot.tasks || [];
    },

    openTasks() {
      return this.tasks.filter((task) => !task.completed);
    },

    doneTasks() {
      return this.tasks.filter((task) => task.completed);
    },

    pomodoro() {
      return this.snapshot.pomodoro || { completed: 0, next_break_type: "short_break" };
    },

    selectedTasks() {
      return this.selectedTaskIds
        .map((taskId) => this.tasks.find((task) => task.id === taskId))
        .filter(Boolean);
    },

    selectedTaskSummary() {
      if (!this.selectedTasks.length) {
        return "不关联任务";
      }
      if (this.selectedTasks.length <= 2) {
        return this.selectedTasks.map((task) => task.title).join("、");
      }
      return `${this.selectedTasks[0].title}、${this.selectedTasks[1].title} 等 ${this.selectedTasks.length} 个任务`;
    },

    recentSessions() {
      return this.snapshot.recent_sessions;
    },

    isFocusing() {
      return Boolean(this.currentSession);
    },

    isPomodoroSession() {
      return this.currentSession?.session_type === "pomodoro";
    },

    elapsedText() {
      return this.formatDuration(this.localElapsed);
    },

    remainingText() {
      const plannedSeconds = (this.currentSession?.planned_minutes || this.settings.session_minutes) * 60;
      return this.formatDuration(Math.max(0, plannedSeconds - this.localElapsed));
    },

    targetText() {
      const minutes = this.currentSession?.planned_minutes ?? this.settings.session_minutes;
      const label = this.sessionTypeLabel(this.currentSession?.session_type || "focus");
      return `${label} · ${minutes} 分钟`;
    },

    blockerLabel() {
      if (!this.blocker.is_admin) {
        return "需管理员权限";
      }
      return this.currentSession?.blocking_active ? "hosts 已写入" : "可写 hosts";
    },

    blockerActiveDomains() {
      return this.blocker.active_domains || [];
    },

    blockerTargetLabel() {
      return `${this.blocker.block_ip || "0.0.0.0"} hosts`;
    },

    blockerStateText() {
      if (this.elevationMessage) {
        return this.elevationMessage;
      }
      if (!this.apiOnline) {
        return "正在连接后端";
      }
      if (!this.blocker.is_admin) {
        return "后端已连接，hosts 需要管理员权限";
      }
      if (this.currentSession?.blocking_active) {
        return "已写入 hosts，网站将解析到 0.0.0.0";
      }
      if (this.currentSession) {
        return "会话进行中，hosts 未生效";
      }
      return "后端已连接，开始专注后写入 hosts";
    },

    blockerDetailText() {
      const hostsPath = this.blocker.hosts_path || "未知 hosts 路径";
      const activeCount = this.blockerActiveDomains.length;
      return activeCount ? `${hostsPath} · 已写入 ${activeCount} 个域名` : `${hostsPath} · 当前未写入`;
    },

    apiStatusText() {
      if (this.syncing) {
        return "同步中";
      }
      if (!this.apiOnline) {
        return this.lastApiError || "等待后端响应";
      }
      return this.lastSyncAt ? `后端已连接 · ${this.lastSyncAt}` : "后端已连接";
    },

    todaySummary() {
      if (this.stats.today_sessions === 0) {
        return "今天还没有记录";
      }
      return `今天 ${this.formatMinutes(this.stats.today_focus_seconds)} · ${this.stats.today_sessions} 场`;
    },

    settingsSummary() {
      const count = this.settings.blocked_domains.length;
      return `${this.settings.session_minutes} 分钟 · ${this.themeModeLabel(this.settings.theme_mode)} · ${this.colorSchemeLabel(this.settings.color_scheme)} · ${count ? `${count} 个网站` : "未设置屏蔽"}`;
    },

    settingsStatusText() {
      if (this.settingsSaveStatus === "saving" || this.settingsSubmitting) {
        return "正在自动保存";
      }
      if (this.settingsSaveStatus === "pending") {
        return "即将自动保存";
      }
      if (this.settingsSaveStatus === "error") {
        return "自动保存失败";
      }
      return "已自动保存";
    },

    pageTitle() {
      if (this.activePage === "tasks") {
        return "任务";
      }
      if (this.activePage === "stats") {
        return "统计";
      }
      if (this.activePage === "settings") {
        return "设置";
      }
      return this.isFocusing ? "进行中" : "专注";
    },

    pageNote() {
      if (this.activePage === "tasks") {
        return this.openTasks.length ? `${this.openTasks.length} 个待办` : "没有待办";
      }
      if (this.activePage === "stats") {
        return this.stats.total_sessions ? `共 ${this.stats.total_sessions} 场` : "暂无记录";
      }
      if (this.activePage === "settings") {
        return this.settingsDirty ? this.settingsStatusText : this.settingsSummary;
      }
      return this.todaySummary;
    },

    nextBreakLabel() {
      return this.pomodoro.next_break_type === "long_break" ? "长休息" : "短休息";
    },

    statusIsWarning() {
      return Boolean(this.currentSession?.blocking_message) || !this.blocker.is_admin;
    },

    statusMessage() {
      if (this.currentSession?.blocking_message) {
        return this.currentSession.blocking_message;
      }
      if (!this.isFocusing) {
        return "按下开始，进入计时。";
      }
      if (this.currentSession.session_type === "pomodoro") {
        const currentTasks = this.tasksForSession(this.currentSession);
        return currentTasks.length ? `正在做：${this.formatTaskList(currentTasks)}` : "番茄钟进行中。";
      }
      if (this.currentSession.session_type === "short_break" || this.currentSession.session_type === "long_break") {
        return "休息中。";
      }
      return "正在计时。";
    },
  },

  methods: {
    async request(path, options = {}) {
      try {
        const response = await fetch(path, {
          headers: {
            "Content-Type": "application/json",
          },
          ...options,
        });
        const payload = await response.json();
        this.apiOnline = true;
        this.lastSyncAt = new Date().toLocaleTimeString("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });

        if (!response.ok) {
          const message = payload.error || `请求失败: ${response.status}`;
          this.lastApiError = message;
          throw new Error(message);
        }

        this.lastApiError = "";
        return payload;
      } catch (error) {
        if (error instanceof TypeError) {
          this.apiOnline = false;
          this.lastApiError = "无法连接后端";
        } else if (!this.lastApiError) {
          this.lastApiError = error.message;
        }
        throw error;
      }
    },

    applySnapshot(snapshot) {
      const normalizedSnapshot = {
        ...snapshot,
        settings: {
          theme_mode: "light",
          color_scheme: "blue",
          daily_quote_enabled: true,
          ...snapshot.settings,
        },
        blocker: {
          is_admin: false,
          hosts_path: "",
          block_ip: "0.0.0.0",
          active_domains: [],
          elevation_supported: false,
          ...(snapshot.blocker || {}),
        },
      };

      this.snapshot = normalizedSnapshot;
      this.localElapsed = normalizedSnapshot.current_session ? normalizedSnapshot.current_session.elapsed_seconds : 0;

      const availableTaskIds = new Set(
        (normalizedSnapshot.tasks || []).filter((task) => !task.completed).map((task) => task.id)
      );
      this.selectedTaskIds = this.selectedTaskIds.filter((taskId) => availableTaskIds.has(taskId));

      if (!this.selectedTaskIds.length && normalizedSnapshot.tasks?.length) {
        const firstOpenTask = normalizedSnapshot.tasks.find((task) => !task.completed);
        this.selectedTaskIds = firstOpenTask ? [firstOpenTask.id] : [];
      }

      if (!this.settingsDirty) {
        this.form.sessionMinutes = normalizedSnapshot.settings.session_minutes;
        this.form.pomodoroMinutes = normalizedSnapshot.settings.pomodoro_minutes;
        this.form.shortBreakMinutes = normalizedSnapshot.settings.short_break_minutes;
        this.form.longBreakMinutes = normalizedSnapshot.settings.long_break_minutes;
        this.form.longBreakEvery = normalizedSnapshot.settings.long_break_every;
        this.form.blockedDomains = [...normalizedSnapshot.settings.blocked_domains];
        this.form.newBlockedDomain = "";
        this.form.themeMode = normalizedSnapshot.settings.theme_mode;
        this.form.colorScheme = normalizedSnapshot.settings.color_scheme;
        this.form.dailyQuoteEnabled = Boolean(normalizedSnapshot.settings.daily_quote_enabled);
      }

      this.rememberPersonalization({
        themeMode: this.form.themeMode,
        colorScheme: this.form.colorScheme,
      });
      this.applyTheme(this.form.themeMode, this.form.colorScheme);

      if (!normalizedSnapshot.settings.daily_quote_enabled) {
        this.dailyQuote = "";
        this.dailyQuoteError = "";
        this.dailyQuoteLoading = false;
      } else if (!this.dailyQuote && !this.dailyQuoteLoading && !this.dailyQuoteError) {
        this.fetchDailyQuote();
      }
    },

    async refreshState() {
      this.syncing = true;
      try {
        const snapshot = await this.request("/api/state");
        this.applySnapshot(snapshot);
      } catch (error) {
        this.setSessionMessage(`状态同步失败：${error.message}`);
      } finally {
        this.syncing = false;
      }
    },

    async fetchDailyQuote() {
      if (!this.form.dailyQuoteEnabled) {
        return;
      }
      this.dailyQuoteLoading = true;
      this.dailyQuoteError = "";
      try {
        const payload = await this.request("/api/yiyan");
        this.dailyQuote = String(payload.quote || "").trim();
        if (!this.dailyQuote) {
          this.dailyQuoteError = "暂时没有取到内容。";
        }
      } catch (error) {
        this.dailyQuoteError = "每日一言暂时不可用。";
      } finally {
        this.dailyQuoteLoading = false;
      }
    },

    async toggleFocus() {
      if (this.isFocusing) {
        await this.stopFocus();
        return;
      }
      await this.startSession("focus");
    },

    async startPomodoro() {
      await this.startSession("pomodoro", this.selectedTaskIds);
    },

    async startBreak(type = this.pomodoro.next_break_type) {
      await this.startSession(type);
    },

    async startSession(sessionType, taskIds = []) {
      this.submitting = true;
      try {
        const normalizedTaskIds = Array.isArray(taskIds) ? taskIds : taskIds ? [taskIds] : [];
        const snapshot = await this.request("/api/focus/start", {
          method: "POST",
          body: JSON.stringify({
            session_type: sessionType,
            task_id: normalizedTaskIds[0] || null,
            task_ids: normalizedTaskIds,
          }),
        });
        this.applySnapshot(snapshot);
      } catch (error) {
        this.setSessionMessage(`操作失败：${error.message}`);
      } finally {
        this.submitting = false;
      }
    },

    async stopFocus() {
      this.submitting = true;
      try {
        const snapshot = await this.request("/api/focus/stop", { method: "POST" });
        this.applySnapshot(snapshot);
      } catch (error) {
        this.setSessionMessage(`操作失败：${error.message}`);
      } finally {
        this.submitting = false;
      }
    },

    async requestElevation() {
      if (this.elevationRequesting || this.blocker.is_admin) {
        return;
      }

      this.elevationRequesting = true;
      this.elevationMessage = "正在发起管理员权限请求。";
      try {
        const payload = await this.request("/api/elevate", { method: "POST" });
        this.elevationMessage = payload.message || "已发起管理员权限请求。";
      } catch (error) {
        this.elevationMessage = `提权失败：${error.message}`;
      } finally {
        this.elevationRequesting = false;
      }
    },

    async saveSettings() {
      if (this.settingsSaveTimer) {
        window.clearTimeout(this.settingsSaveTimer);
        this.settingsSaveTimer = null;
      }

      this.settingsSubmitting = true;
      this.settingsSaveStatus = "saving";
      try {
        const snapshot = await this.request("/api/settings", {
          method: "POST",
          body: JSON.stringify(this.buildSettingsPayload()),
        });
        this.settingsDirty = false;
        this.settingsSaveStatus = "saved";
        this.rememberPersonalization({
          themeMode: this.form.themeMode,
          colorScheme: this.form.colorScheme,
        });
        this.applySnapshot(snapshot);
      } catch (error) {
        this.settingsSaveStatus = "error";
        this.setSessionMessage(`保存失败：${error.message}`);
      } finally {
        this.settingsSubmitting = false;
      }
    },

    scheduleSettingsSave(delay = 650) {
      this.settingsDirty = true;
      this.settingsSaveStatus = "pending";
      if (this.settingsSaveTimer) {
        window.clearTimeout(this.settingsSaveTimer);
      }
      this.settingsSaveTimer = window.setTimeout(() => {
        this.saveSettings();
      }, delay);
    },

    markSettingsChanged() {
      this.scheduleSettingsSave();
    },

    addBlockedDomain() {
      const domain = normalizeDomainInput(this.form.newBlockedDomain);
      if (!domain || this.form.blockedDomains.includes(domain)) {
        this.form.newBlockedDomain = "";
        return;
      }
      this.form.blockedDomains.push(domain);
      this.form.newBlockedDomain = "";
      this.scheduleSettingsSave(120);
    },

    removeBlockedDomain(domain) {
      this.form.blockedDomains = this.form.blockedDomains.filter((item) => item !== domain);
      this.scheduleSettingsSave(120);
    },

    selectThemeMode(value) {
      this.form.themeMode = value;
      this.updateAppearance();
    },

    selectColorScheme(value) {
      this.form.colorScheme = value;
      this.updateAppearance();
    },

    updateAppearance() {
      this.rememberPersonalization({
        themeMode: this.form.themeMode,
        colorScheme: this.form.colorScheme,
      });
      this.applyTheme(this.form.themeMode, this.form.colorScheme);
      this.scheduleSettingsSave(180);
    },

    rememberPersonalization(patch = {}) {
      const current = readPersonalization();
      const next = {
        ...current,
        ...patch,
      };
      try {
        window.localStorage.setItem(PERSONALIZATION_KEY, JSON.stringify(next));
      } catch {
        // Local storage can be unavailable in restricted browser contexts.
      }
    },

    buildSettingsPayload() {
      return {
        session_minutes: Number(this.form.sessionMinutes),
        pomodoro_minutes: Number(this.form.pomodoroMinutes),
        short_break_minutes: Number(this.form.shortBreakMinutes),
        long_break_minutes: Number(this.form.longBreakMinutes),
        long_break_every: Number(this.form.longBreakEvery),
        blocked_domains: this.form.blockedDomains
          .map((domain) => normalizeDomainInput(domain))
          .filter((domain, index, domains) => domain && domains.indexOf(domain) === index),
        theme_mode: this.form.themeMode,
        color_scheme: this.form.colorScheme,
        daily_quote_enabled: this.form.dailyQuoteEnabled,
      };
    },

    flushSettingsBeforeUnload() {
      if (!this.settingsDirty && !this.settingsSaveTimer) {
        return;
      }
      if (this.settingsSaveTimer) {
        window.clearTimeout(this.settingsSaveTimer);
        this.settingsSaveTimer = null;
      }

      const body = JSON.stringify(this.buildSettingsPayload());
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: "application/json" });
        navigator.sendBeacon("/api/settings", blob);
        return;
      }

      fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      }).catch(() => {});
    },

    applyTheme(themeMode = "light", colorScheme = "blue") {
      const theme = VALID_THEME_MODES.includes(themeMode) ? themeMode : "light";
      const color = VALID_COLOR_SCHEMES.includes(colorScheme) ? colorScheme : "blue";
      document.documentElement.dataset.theme = theme;
      document.documentElement.dataset.color = color;
    },

    themeModeLabel(value) {
      return this.themeOptions.find((item) => item.value === value)?.label || "浅色";
    },

    colorSchemeLabel(value) {
      return this.colorOptions.find((item) => item.value === value)?.label || "淡蓝";
    },

    selectPage(page) {
      if (!VALID_PAGES.includes(page)) {
        return;
      }
      this.activePage = page;
      this.rememberPersonalization({ activePage: page });
      if (page === "tasks") {
        this.taskMessage = "";
      }
    },

    async addTask() {
      const title = this.newTaskTitle.trim();
      if (!title || this.taskSubmitting) {
        this.taskMessage = title ? "" : "先写一点任务内容。";
        return;
      }

      this.taskSubmitting = true;
      this.taskMessage = "";
      try {
        const snapshot = await this.request("/api/tasks", {
          method: "POST",
          body: JSON.stringify({ title }),
        });
        this.newTaskTitle = "";
        this.applySnapshot(snapshot);
        this.activePage = "tasks";
      } catch (error) {
        this.taskMessage = `添加失败：${error.message}`;
      } finally {
        this.taskSubmitting = false;
      }
    },

    async toggleTask(task) {
      if (this.taskSubmitting) {
        return;
      }

      this.taskSubmitting = true;
      this.taskMessage = "";
      try {
        const snapshot = await this.request(`/api/tasks/${task.id}`, {
          method: "POST",
          body: JSON.stringify({ completed: !task.completed }),
        });
        this.applySnapshot(snapshot);
      } catch (error) {
        this.taskMessage = `更新失败：${error.message}`;
      } finally {
        this.taskSubmitting = false;
      }
    },

    async deleteTask(task) {
      if (this.taskSubmitting) {
        return;
      }

      this.taskSubmitting = true;
      this.taskMessage = "";
      try {
        const snapshot = await this.request(`/api/tasks/${task.id}`, {
          method: "POST",
          body: JSON.stringify({ _delete: true }),
        });
        this.selectedTaskIds = this.selectedTaskIds.filter((taskId) => taskId !== task.id);
        this.applySnapshot(snapshot);
      } catch (error) {
        this.taskMessage = `删除失败：${error.message}`;
      } finally {
        this.taskSubmitting = false;
      }
    },

    toggleSelectedTask(task) {
      const exists = this.selectedTaskIds.includes(task.id);
      this.selectedTaskIds = exists
        ? this.selectedTaskIds.filter((taskId) => taskId !== task.id)
        : [...this.selectedTaskIds, task.id];
    },

    tasksForSession(session) {
      const taskIds = Array.isArray(session?.task_ids) && session.task_ids.length
        ? session.task_ids
        : session?.task_id
          ? [session.task_id]
          : [];
      return taskIds
        .map((taskId) => this.tasks.find((task) => task.id === taskId))
        .filter(Boolean);
    },

    formatTaskList(tasks) {
      if (tasks.length <= 2) {
        return tasks.map((task) => task.title).join("、");
      }
      return `${tasks[0].title}、${tasks[1].title} 等 ${tasks.length} 个任务`;
    },

    toggleDailyQuoteEnabled() {
      if (!this.form.dailyQuoteEnabled) {
        this.dailyQuote = "";
        this.dailyQuoteError = "";
        this.dailyQuoteLoading = false;
      } else if (!this.dailyQuote && !this.dailyQuoteLoading) {
        this.fetchDailyQuote();
      }
      this.scheduleSettingsSave(120);
    },

    setSessionMessage(message) {
      if (this.currentSession) {
        this.snapshot.current_session.blocking_message = message;
      }
    },

    sessionTypeLabel(type) {
      if (type === "pomodoro") {
        return "番茄钟";
      }
      if (type === "short_break") {
        return "短休息";
      }
      if (type === "long_break") {
        return "长休息";
      }
      return "专注";
    },

    formatDuration(totalSeconds) {
      const seconds = Math.max(0, Number(totalSeconds || 0));
      const hours = Math.floor(seconds / 3600);
      const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
      const remaining = String(seconds % 60).padStart(2, "0");

      if (hours === 0) {
        return `${minutes}:${remaining}`;
      }
      return `${String(hours).padStart(2, "0")}:${minutes}:${remaining}`;
    },

    formatMinutes(totalSeconds) {
      const minutes = Math.round((Number(totalSeconds || 0) / 60) * 10) / 10;
      return `${minutes} 分钟`;
    },

    formatDateRange(item) {
      const start = new Date(item.started_at);
      const end = new Date(item.ended_at);
      return `${this.sessionTypeLabel(item.session_type)} · ${start.toLocaleString("zh-CN", {
        month: "numeric",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })} - ${end.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
      })}`;
    },
  },

  mounted() {
    this.applyTheme(this.form.themeMode, this.form.colorScheme);
    this.rememberPersonalization({ activePage: this.activePage });
    window.addEventListener("beforeunload", this.flushSettingsBeforeUnload);
    this.refreshState();
    this.refreshTimer = window.setInterval(this.refreshState, 5000);
    this.tickTimer = window.setInterval(() => {
      if (this.currentSession) {
        this.localElapsed += 1;
      }
    }, 1000);
  },

  beforeUnmount() {
    window.removeEventListener("beforeunload", this.flushSettingsBeforeUnload);
    if (this.refreshTimer) {
      window.clearInterval(this.refreshTimer);
    }
    if (this.tickTimer) {
      window.clearInterval(this.tickTimer);
    }
    if (this.settingsSaveTimer) {
      window.clearTimeout(this.settingsSaveTimer);
    }
  },
});

app.mount("#app");
