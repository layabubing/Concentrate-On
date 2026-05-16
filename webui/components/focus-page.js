window.FocusPage = {
  template: `
    <section class="page page-focus" aria-label="专注">
      <section class="focus-card" aria-labelledby="focus-title">
        <div class="timer-block">
          <p id="focus-title" class="label">{{ $root.isFocusing ? $root.sessionTypeLabel($root.currentSession.session_type) : "准备中" }}</p>
          <strong class="timer">{{ $root.isFocusing ? $root.remainingText : $root.elapsedText }}</strong>
          <p class="target">{{ $root.isFocusing ? '剩余 · ' + $root.targetText : $root.targetText }}</p>
        </div>

        <button class="main-action" :class="{ active: $root.isFocusing }" :disabled="$root.submitting" @click="$root.toggleFocus">
          {{ $root.isFocusing ? "结束" : "开始" }}
        </button>

        <p class="message" :class="{ warning: $root.statusIsWarning }">{{ $root.statusMessage }}</p>
      </section>

      <section v-if="$root.settings.daily_quote_enabled" class="daily-quote-card panel" aria-label="每日一言">
        <div class="daily-quote-head">
          <span>每日一言</span>
          <button class="quote-refresh-button" type="button" :disabled="$root.dailyQuoteLoading" @click="$root.fetchDailyQuote">
            {{ $root.dailyQuoteLoading ? "获取中" : "换一句" }}
          </button>
        </div>
        <p v-if="$root.dailyQuote" class="daily-quote-text">{{ $root.dailyQuote }}</p>
        <p v-else class="daily-quote-text muted">{{ $root.dailyQuoteError || "正在获取一句话。" }}</p>
      </section>

      <section class="pomodoro-card panel">
        <div class="section-head compact-head">
          <div>
            <h2>番茄钟</h2>
            <small>已完成 {{ $root.pomodoro.completed }} 个，下一次休息：{{ $root.nextBreakLabel }}</small>
          </div>
        </div>
        <div class="pomodoro-actions">
          <section class="task-bind-picker" aria-label="绑定任务">
            <div class="task-bind-head">
              <span>绑定任务</span>
              <small>{{ $root.selectedTaskSummary }}</small>
            </div>
            <div v-if="!$root.openTasks.length" class="task-bind-empty">没有可绑定的待办任务。</div>
            <div v-else class="task-bind-list">
              <label v-for="task in $root.openTasks" :key="task.id" class="task-bind-option">
                <input
                  type="checkbox"
                  :checked="$root.selectedTaskIds.includes(task.id)"
                  :disabled="$root.isFocusing"
                  @change="$root.toggleSelectedTask(task)"
                />
                <span>{{ task.title }}</span>
              </label>
            </div>
          </section>
          <button class="save-button" type="button" :disabled="$root.submitting || $root.isFocusing" @click="$root.startPomodoro">开始番茄钟</button>
          <button class="subtle-button" type="button" :disabled="$root.submitting || $root.isFocusing" @click="$root.startBreak()">开始休息</button>
        </div>
      </section>

      <section class="quick-status" aria-label="当前设置">
        <article class="quiet-card">
          <span>今日</span>
          <strong>{{ $root.formatMinutes($root.stats.today_focus_seconds) }}</strong>
          <small>{{ $root.stats.today_sessions }} 场</small>
        </article>
        <article class="quiet-card">
          <span>屏蔽</span>
          <strong>{{ $root.settings.blocked_domains.length }} 个</strong>
          <small>{{ $root.blockerLabel }}</small>
        </article>
      </section>
    </section>
  `,
};
