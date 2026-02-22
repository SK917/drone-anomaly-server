<script setup lang="ts">
    import Header from './components/Header.vue';
    import Footer from './components/Footer.vue';
    import { RouterView } from 'vue-router';
</script>

<template>
    <div class="bg-slate-900 h-screen flex flex-col overflow-hidden">
        <Header />

        <main class="flex-1 flex flex-col min-h-0">
          <RouterView />
        </main>

        <Footer />
    </div>
</template>

<style scoped></style>
