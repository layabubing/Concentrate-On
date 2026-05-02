window.SettingsPage = {
  template: `
    <section class="page page-settings" aria-label="设置">
      <section class="panel settings-panel">
        <div class="section-head">
          <h2>设置</h2>
          <small>{{ $root.settingsSummary }}</small>
        </div>
        <form class="settings-form" @submit.prevent="$root.saveSettings">
          <label class="field inline-field">
            <span>默认时长</span>
            <input v-model.number="$root.form.sessionMinutes" type="number" min="5" max="240" @input="$root.settingsDirty = true" />
            <em>分钟</em>
          </label>
          <label class="field inline-field">
            <span>番茄钟</span>
            <input v-model.number="$root.form.pomodoroMinutes" type="number" min="5" max="120" @input="$root.settingsDirty = true" />
            <em>分钟</em>
          </label>
          <label class="field inline-field">
            <span>短休息</span>
            <input v-model.number="$root.form.shortBreakMinutes" type="number" min="1" max="60" @input="$root.settingsDirty = true" />
            <em>分钟</em>
          </label>
          <label class="field inline-field">
            <span>长休息</span>
            <input v-model.number="$root.form.longBreakMinutes" type="number" min="1" max="90" @input="$root.settingsDirty = true" />
            <em>分钟</em>
          </label>
          <label class="field inline-field">
            <span>长休息间隔</span>
            <input v-model.number="$root.form.longBreakEvery" type="number" min="2" max="12" @input="$root.settingsDirty = true" />
            <em>个番茄</em>
          </label>

          <label class="field">
            <span>需要屏蔽的网站</span>
            <textarea
              v-model="$root.form.blockedDomainsText"
              rows="7"
              placeholder="每行一个域名，例如：baidu.com"
              @input="$root.settingsDirty = true"
            ></textarea>
          </label>

          <div class="form-actions">
            <button class="subtle-button" type="button" :disabled="$root.syncing" @click="$root.refreshState">
              {{ $root.syncing ? "同步中" : "同步" }}
            </button>
            <button class="save-button" type="submit" :disabled="$root.submitting">
              {{ $root.submitting ? "保存中" : "保存" }}
            </button>
          </div>
        </form>
      </section>
    </section>
  `,
};
