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

      <section class="pomodoro-card panel">
        <div class="section-head compact-head">
          <div>
            <h2>番茄钟</h2>
            <small>已完成 {{ $root.pomodoro.completed }} 个，下一次休息：{{ $root.nextBreakLabel }}</small>
          </div>
        </div>
        <div class="pomodoro-actions">
          <select v-model="$root.selectedTaskId" :disabled="$root.isFocusing">
            <option value="">不关联任务</option>
            <option v-for="task in $root.openTasks" :key="task.id" :value="task.id">{{ task.title }}</option>
          </select>
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
