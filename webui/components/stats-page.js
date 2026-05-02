window.StatsPage = {
  template: `
    <section class="page page-stats" aria-label="统计">
      <section class="stats-grid">
        <article class="stat-card panel">
          <span>今天</span>
          <strong>{{ $root.formatMinutes($root.stats.today_focus_seconds) }}</strong>
          <small>{{ $root.stats.today_sessions }} 场</small>
        </article>
        <article class="stat-card panel">
          <span>总计</span>
          <strong>{{ $root.formatMinutes($root.stats.total_focus_seconds) }}</strong>
          <small>{{ $root.stats.total_sessions }} 场</small>
        </article>
        <article class="stat-card panel">
          <span>番茄</span>
          <strong>{{ $root.pomodoro.completed }} 个</strong>
          <small>{{ $root.settings.pomodoro_minutes }} 分钟 / 个</small>
        </article>
      </section>

      <section class="panel history-panel">
        <div class="section-head">
          <h2>最近记录</h2>
          <small>{{ $root.recentSessions.length ? '最近 ' + $root.recentSessions.length + ' 场' : "暂无记录" }}</small>
        </div>
        <div v-if="!$root.recentSessions.length" class="empty-state">还没有专注记录。</div>
        <div v-else class="history-list">
          <article v-for="item in $root.recentSessions" :key="item.ended_at" class="history-item">
            <strong>{{ $root.formatMinutes(item.duration_seconds) }}</strong>
            <span>{{ $root.formatDateRange(item) }}</span>
          </article>
        </div>
      </section>
    </section>
  `,
};
