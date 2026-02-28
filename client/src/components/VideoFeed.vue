<script setup lang="ts">
    import { useFramesStore } from '@/stores/frames-store';
    import { useStatsStore } from '@/stores/stats-store';

    const framesStore = useFramesStore();
    const statsStore = useStatsStore();

</script>

<template>
    <div class="p-0.5 w-full max-w-2xl aspect-video bg-gray-800 border-20 border-gray-800 outline outline-transparent rounded-sm
    hover:outline-yellow-600">
        <img
            v-if="statsStore.has_stream && statsStore.has_stream!=null"
            :src="framesStore.frameUrl"
            class="w-full h-full object-contain"
            alt="Video feed"
        />
        <div v-else class="w-full h-full flex items-center justify-center bg-gray-800 text-gray-400 text-lg font-orbit">
            No stream input.
        </div>
    </div>
</template>