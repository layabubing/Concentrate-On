const app = Vue.createApp({
  data() {
    return {
      snapshot: {
        settings: {
          blocked_domains: [],
          session_minutes: 45,
        },
        current_session: null,
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
      form: {
        sessionMinutes: 45,
        blockedDomainsText: "",
      },
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

    recentSessions() {
      return this.snapshot.recent_sessions;
    },

    isFocusing() {
      return Boolean(this.currentSession);
    },

    elapsedText() {
      return this.formatDuration(this.localElapsed);
    },

    targetText() {
      const minutes = this.currentSession?.planned_minutes ?? this.settings.session_minutes;
      return `目标 ${minutes} 分钟`;
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
      return `${this.settings.session_minutes} 分钟 · ${count ? `${count} 个网站` : "未设置屏蔽"}`;
    },

    statusIsWarning() {
      return Boolean(this.currentSession?.blocking_message) || !this.blocker.is_admin;
    },

    statusMessage() {
      if (this.currentSession?.blocking_message) {
        return this.currentSession.blocking_message;
      }
      if (this.isFocusing) {
        return "专注进行中。";
      }
      return "只保留必要操作，开始后自动计时并应用屏蔽设置。";
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
      this.snapshot = snapshot;
      this.localElapsed = snapshot.current_session ? snapshot.current_session.elapsed_seconds : 0;

      if (!this.settingsDirty) {
        this.form.sessionMinutes = snapshot.settings.session_minutes;
        this.form.blockedDomainsText = snapshot.settings.blocked_domains.join("\n");
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

    async toggleFocus() {
      this.submitting = true;
      try {
        const path = this.isFocusing ? "/api/focus/stop" : "/api/focus/start";
        const snapshot = await this.request(path, { method: "POST" });
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
            blocked_domains: this.form.blockedDomainsText,
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

    setSessionMessage(message) {
      if (this.currentSession) {
        this.snapshot.current_session.blocking_message = message;
      }
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
      return `${start.toLocaleString("zh-CN", {
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
