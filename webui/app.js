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
        },
      },
      navItems: [
        { key: "focus", label: "专注", icon: "◐" },
        { key: "tasks", label: "任务", icon: "□" },
        { key: "stats", label: "统计", icon: "▦" },
        { key: "settings", label: "设置", icon: "◎" },
      ],
      activePage: "focus",
      selectedTaskId: "",
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
        themeMode: "light",
        colorScheme: "blue",
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
      syncing: false,
      localElapsed: 0,
      refreshTimer: null,
      tickTimer: null,
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

    selectedTask() {
      return this.tasks.find((task) => task.id === this.selectedTaskId) || null;
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
      return this.blocker.is_admin ? "可用" : "需管理员权限";
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
        return this.settingsDirty ? "未保存" : this.settingsSummary;
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
        return this.selectedTask ? `正在做：${this.selectedTask.title}` : "番茄钟进行中。";
      }
      if (this.currentSession.session_type === "short_break" || this.currentSession.session_type === "long_break") {
        return "休息中。";
      }
      return "正在计时。";
    },
  },

  methods: {
    async request(path, options = {}) {
      const response = await fetch(path, {
        headers: {
          "Content-Type": "application/json",
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`请求失败: ${response.status}`);
      }

      return response.json();
    },

    applySnapshot(snapshot) {
      const normalizedSnapshot = {
        ...snapshot,
        settings: {
          theme_mode: "light",
          color_scheme: "blue",
          ...snapshot.settings,
        },
      };
      this.snapshot = normalizedSnapshot;
      this.localElapsed = normalizedSnapshot.current_session ? normalizedSnapshot.current_session.elapsed_seconds : 0;

      if (!this.selectedTaskId && normalizedSnapshot.tasks?.length) {
        const firstOpenTask = normalizedSnapshot.tasks.find((task) => !task.completed);
        this.selectedTaskId = firstOpenTask?.id || "";
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
      }

      this.applyTheme(this.form.themeMode, this.form.colorScheme);
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

    async toggleFocus() {
      if (this.isFocusing) {
        await this.stopFocus();
        return;
      }
      await this.startSession("focus");
    },

    async startPomodoro() {
      await this.startSession("pomodoro", this.selectedTaskId || null);
    },

    async startBreak(type = this.pomodoro.next_break_type) {
      await this.startSession(type);
    },

    async startSession(sessionType, taskId = null) {
      this.submitting = true;
      try {
        const snapshot = await this.request("/api/focus/start", {
          method: "POST",
          body: JSON.stringify({
            session_type: sessionType,
            task_id: taskId,
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

    async saveSettings() {
      this.submitting = true;
      try {
        const snapshot = await this.request("/api/settings", {
          method: "POST",
          body: JSON.stringify({
            session_minutes: Number(this.form.sessionMinutes),
            pomodoro_minutes: Number(this.form.pomodoroMinutes),
            short_break_minutes: Number(this.form.shortBreakMinutes),
            long_break_minutes: Number(this.form.longBreakMinutes),
            long_break_every: Number(this.form.longBreakEvery),
            blocked_domains: this.form.blockedDomains,
            theme_mode: this.form.themeMode,
            color_scheme: this.form.colorScheme,
          }),
        });
        this.settingsDirty = false;
        this.applySnapshot(snapshot);
      } catch (error) {
        this.setSessionMessage(`保存失败：${error.message}`);
      } finally {
        this.submitting = false;
      }
    },

    addBlockedDomain() {
      const domain = this.form.newBlockedDomain.trim().toLowerCase();
      if (!domain || this.form.blockedDomains.includes(domain)) {
        this.form.newBlockedDomain = "";
        return;
      }
      this.form.blockedDomains.push(domain);
      this.form.newBlockedDomain = "";
      this.settingsDirty = true;
    },

    removeBlockedDomain(domain) {
      this.form.blockedDomains = this.form.blockedDomains.filter((item) => item !== domain);
      this.settingsDirty = true;
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
      this.settingsDirty = true;
      this.applyTheme(this.form.themeMode, this.form.colorScheme);
    },

    applyTheme(themeMode = "light", colorScheme = "blue") {
      const theme = this.themeOptions.some((item) => item.value === themeMode) ? themeMode : "light";
      const color = this.colorOptions.some((item) => item.value === colorScheme) ? colorScheme : "blue";
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
      this.activePage = page;
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
        if (this.selectedTaskId === task.id) {
          this.selectedTaskId = "";
        }
        this.applySnapshot(snapshot);
      } catch (error) {
        this.taskMessage = `删除失败：${error.message}`;
      } finally {
        this.taskSubmitting = false;
      }
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
    this.refreshState();
    this.refreshTimer = window.setInterval(this.refreshState, 5000);
    this.tickTimer = window.setInterval(() => {
      if (this.currentSession) {
        this.localElapsed += 1;
      }
    }, 1000);
  },

  beforeUnmount() {
    if (this.refreshTimer) {
      window.clearInterval(this.refreshTimer);
    }
    if (this.tickTimer) {
      window.clearInterval(this.tickTimer);
    }
  },
});

app.mount("#app");
