<script setup lang="ts">
    import Header from './components/Header.vue';
    import Footer from './components/Footer.vue';
    import { RouterView } from 'vue-router';
</script>

<template>
    <div class="bg-slate-700 min-h-screen flex flex-col">
        <Header />

        <main class="flex-1">
          <RouterView />
        </main>

        <Footer />
    </div>
</template>

<style scoped></style>
