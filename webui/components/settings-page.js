window.SettingsPage = {
  template: `
    <section class="page page-settings" aria-label="设置">
      <section class="panel settings-panel">
        <div class="section-head">
          <h2>设置</h2>
          <small>{{ $root.settingsSummary }}</small>
        </div>
        <form class="settings-form" @submit.prevent="$root.saveSettings">
          <section class="field appearance-field" aria-label="主题模式">
            <span>主题</span>
            <div class="option-row">
              <button
                v-for="theme in $root.themeOptions"
                :key="theme.value"
                class="option-button"
                :class="{ active: $root.form.themeMode === theme.value }"
                type="button"
                @click="$root.selectThemeMode(theme.value)"
              >
                {{ theme.label }}
              </button>
            </div>
          </section>

          <section class="field appearance-field" aria-label="主题配色">
            <span>配色</span>
            <div class="option-row color-options">
              <button
                v-for="color in $root.colorOptions"
                :key="color.value"
                class="option-button color-option"
                :class="{ active: $root.form.colorScheme === color.value }"
                :data-color-option="color.value"
                type="button"
                @click="$root.selectColorScheme(color.value)"
              >
                <i aria-hidden="true"></i>
                {{ color.label }}
              </button>
            </div>
          </section>

          <label class="field inline-field">
            <span>默认时长</span>
            <input v-model.number="$root.form.sessionMinutes" type="number" min="5" max="240" @input="$root.markSettingsChanged" />
            <em>分钟</em>
          </label>
          <label class="field inline-field">
            <span>番茄钟</span>
            <input v-model.number="$root.form.pomodoroMinutes" type="number" min="5" max="120" @input="$root.markSettingsChanged" />
            <em>分钟</em>
          </label>
          <label class="field inline-field">
            <span>短休息</span>
            <input v-model.number="$root.form.shortBreakMinutes" type="number" min="1" max="60" @input="$root.markSettingsChanged" />
            <em>分钟</em>
          </label>
          <label class="field inline-field">
            <span>长休息</span>
            <input v-model.number="$root.form.longBreakMinutes" type="number" min="1" max="90" @input="$root.markSettingsChanged" />
            <em>分钟</em>
          </label>
          <label class="field inline-field">
            <span>长休息间隔</span>
            <input v-model.number="$root.form.longBreakEvery" type="number" min="2" max="12" @input="$root.markSettingsChanged" />
            <em>个番茄</em>
          </label>

          <section class="field domain-field" aria-label="需要屏蔽的网站">
            <span>需要屏蔽的网站</span>
            <div class="domain-add-row">
              <input
                v-model="$root.form.newBlockedDomain"
                type="text"
                placeholder="输入域名，例如：baidu.com"
                autocomplete="off"
                @keydown.enter.prevent="$root.addBlockedDomain"
              />
              <button class="subtle-button" type="button" @click="$root.addBlockedDomain">添加</button>
            </div>

            <div v-if="!$root.form.blockedDomains.length" class="domain-empty">还没有添加网站。</div>
            <div v-else class="domain-list">
              <span v-for="domain in $root.form.blockedDomains" :key="domain" class="domain-chip">
                {{ domain }}
                <button type="button" aria-label="移除网站" @click="$root.removeBlockedDomain(domain)">×</button>
              </span>
            </div>
          </section>

          <div class="form-actions">
            <span class="autosave-status" :class="$root.settingsSaveStatus">{{ $root.settingsStatusText }}</span>
            <button class="subtle-button" type="button" :disabled="$root.syncing" @click="$root.refreshState">
              {{ $root.syncing ? "同步中" : "同步" }}
            </button>
          </div>
        </form>
      </section>
    </section>
  `,
};
