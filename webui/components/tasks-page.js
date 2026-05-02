window.TasksPage = {
  template: `
    <section class="page page-tasks" aria-label="任务">
      <section class="panel task-panel">
        <form class="task-form" @submit.prevent="$root.addTask">
          <input v-model="$root.newTaskTitle" type="text" placeholder="添加一个任务" autocomplete="off" />
          <button class="save-button" type="submit" :disabled="$root.taskSubmitting">
            {{ $root.taskSubmitting ? "添加中" : "添加" }}
          </button>
        </form>
        <p v-if="$root.taskMessage" class="task-message">{{ $root.taskMessage }}</p>

        <div v-if="!$root.tasks.length" class="empty-state">还没有任务。</div>
        <div v-else class="task-list">
          <article v-for="task in $root.openTasks" :key="task.id" class="task-item">
            <label>
              <input type="checkbox" :checked="task.completed" :disabled="$root.taskSubmitting" @change="$root.toggleTask(task)" />
              <span>{{ task.title }}</span>
            </label>
            <div class="task-meta">
              <small>🍅 {{ task.pomodoros }}</small>
              <button type="button" :disabled="$root.taskSubmitting" @click="$root.deleteTask(task)">删除</button>
            </div>
          </article>
          <article v-for="task in $root.doneTasks" :key="task.id" class="task-item done">
            <label>
              <input type="checkbox" :checked="task.completed" :disabled="$root.taskSubmitting" @change="$root.toggleTask(task)" />
              <span>{{ task.title }}</span>
            </label>
            <div class="task-meta">
              <small>🍅 {{ task.pomodoros }}</small>
              <button type="button" :disabled="$root.taskSubmitting" @click="$root.deleteTask(task)">删除</button>
            </div>
          </article>
        </div>
      </section>
    </section>
  `,
};
