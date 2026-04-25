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
      activePane: "settings",
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
      return this.blocker.is_admin ? "已具备管理员权限" : "缺少管理员权限";
    },

    statusMessage() {
      if (this.currentSession?.blocking_message) {
        return this.currentSession.blocking_message;
      }
      if (this.isFocusing) {
        return "专注进行中，界面会持续和 Python 后端同步。";
      }
      return "轻点开始按钮，进入下一段清晰、安静、不被打断的工作时间。";
    },

    ringStyle() {
      const plannedMinutes = this.currentSession?.planned_minutes ?? this.settings.session_minutes;
      const totalSeconds = Math.max(1, plannedMinutes * 60);
      const progress = Math.min(this.localElapsed / totalSeconds, 1);
      const degrees = Math.max(24, Math.round(progress * 360));
      return {
        "--progress": `${degrees}deg`,
      };
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

      if (!snapshot.current_session && this.activePane === "history" && snapshot.recent_sessions.length === 0) {
        this.activePane = "settings";
      }
    },

    async refreshState() {
      this.syncing = true;
      try {
        const snapshot = await this.request("/api/state");
        this.applySnapshot(snapshot);
      } catch (error) {
        if (this.currentSession) {
          this.snapshot.current_session.blocking_message = `状态同步失败：${error.message}`;
        }
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
        if (!this.isFocusing) {
          this.activePane = "history";
        }
      } catch (error) {
        if (this.currentSession) {
          this.snapshot.current_session.blocking_message = `操作失败：${error.message}`;
        }
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
        if (this.currentSession) {
          this.snapshot.current_session.blocking_message = `保存失败：${error.message}`;
        }
      } finally {
        this.submitting = false;
      }
    },

    formatDuration(totalSeconds) {
      const seconds = Math.max(0, Number(totalSeconds || 0));
      const hours = String(Math.floor(seconds / 3600)).padStart(2, "0");
      const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
      const remaining = String(seconds % 60).padStart(2, "0");
      return `${hours}:${minutes}:${remaining}`;
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
