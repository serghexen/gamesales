<template>
  <div class="loader-wrap loader-wrap--compact">
    <div aria-label="Хомяк бежит в колесе" role="img" class="wheel-and-hamster wheel-and-hamster--mini">
      <div class="wheel"></div>
      <div class="hamster">
        <div class="hamster__body">
          <div class="hamster__head">
            <div class="hamster__ear"></div>
            <div class="hamster__eye"></div>
            <div class="hamster__nose"></div>
          </div>
          <div class="hamster__limb hamster__limb--fr"></div>
          <div class="hamster__limb hamster__limb--fl"></div>
          <div class="hamster__limb hamster__limb--br"></div>
          <div class="hamster__limb hamster__limb--bl"></div>
          <div class="hamster__tail"></div>
        </div>
      </div>
      <div class="spoke"></div>
    </div>
    <p class="muted">{{ label }}</p>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, default: 'Загрузка…' },
})
</script>
