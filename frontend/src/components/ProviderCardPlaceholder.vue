<template>
  <article class="placeholder-card" aria-hidden="true">
    <header class="placeholder-head">
      <span class="skeleton mark" />
      <span class="heading">
        <span class="skeleton wordmark" />
        <span class="skeleton plan" />
      </span>
      <span class="skeleton badge" />
    </header>

    <div class="placeholder-body">
      <span class="skeleton eyebrow" />
      <span class="skeleton figure" />
      <span class="skeleton meter" />
      <span class="skeleton meter short" />
    </div>

    <footer class="placeholder-foot">
      <span class="skeleton footline" />
      <span class="skeleton footline short" />
    </footer>
  </article>
</template>

<style scoped>
.placeholder-card {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 1.25rem;
  background: #16161a;
  padding: 0.95rem 1.1rem 0.75rem;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 4%),
    0 6px 14px rgb(0 0 0 / 40%);
}

.placeholder-head,
.placeholder-foot {
  display: flex;
  align-items: center;
}

.placeholder-head {
  gap: 0.75rem;
}

.heading {
  display: grid;
  flex: 1;
  gap: 0.35rem;
}

.placeholder-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  min-height: 0;
}

.placeholder-foot {
  justify-content: space-between;
  gap: 1rem;
  border-top: 1px solid rgb(255 255 255 / 7%);
  padding-top: 0.65rem;
}

.skeleton {
  display: block;
  overflow: hidden;
  border-radius: 999px;
  background: rgb(255 255 255 / 7%);
}

.skeleton::after {
  content: "";
  display: block;
  width: 45%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgb(255 255 255 / 9%), transparent);
  animation: shimmer 1.4s ease-in-out infinite;
  transform: translateX(-120%);
}

.mark {
  width: 2.5rem;
  height: 2.5rem;
  flex: none;
  border-radius: 0.8rem;
}

.wordmark {
  width: min(9rem, 75%);
  height: 0.9rem;
}

.plan {
  width: min(6rem, 52%);
  height: 0.55rem;
}

.badge {
  width: 4.5rem;
  height: 1.25rem;
  flex: none;
}

.eyebrow {
  width: 9rem;
  height: 0.55rem;
}

.figure {
  width: 7.5rem;
  height: 2.8rem;
  margin-top: 0.45rem;
  border-radius: 0.55rem;
}

.meter {
  width: 100%;
  height: 0.65rem;
  margin-top: 1.15rem;
}

.meter.short {
  width: 72%;
  margin-top: 0.8rem;
}

.footline {
  width: 7.5rem;
  height: 0.5rem;
}

.footline.short {
  width: 5rem;
}

@keyframes shimmer {
  to {
    transform: translateX(300%);
  }
}
</style>
