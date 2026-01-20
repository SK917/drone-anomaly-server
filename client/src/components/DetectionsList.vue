<script setup lang="ts">
    import { useDetectionsStore } from '@/stores/detections-store';
    import type { Detection, DetectionsResponse } from '@/services/types';
    import DetectionCard from './DetectionCard.vue';

    const detectionsStore = useDetectionsStore();

</script>

<template>
    <div class="m-4 w-180 h-120 bg-gray-800 rounded-sm p-2 overflow-y-auto detections-scroll">
        <div v-if="detectionsStore.detections.length===0" class="w-full h-full flex items-center justify-center text-gray-400 text-lg">
            No detections.
        </div>
        <DetectionCard
        v-else
        v-for="item in detectionsStore.groupedDetections"
        :key="item.detection.class_id"
        :detect="item.detection"
        :numDetects="item.numDetects"
        />
    </div>
</template>

<style scoped>
    /* Chrome, Edge, Safari */
    .detections-scroll::-webkit-scrollbar {
    width: 8px;
    }

    .detections-scroll::-webkit-scrollbar-track {
    background: #1f2937; /* gray-800 */
    }

    .detections-scroll::-webkit-scrollbar-thumb {
    background-color: #4b5563; /* gray-600 */
    border-radius: 6px;
    }

    .detections-scroll::-webkit-scrollbar-thumb:hover {
    background-color: #6b7280; /* gray-500 */
    }

    /* Firefox */
    .detections-scroll {
    scrollbar-width: thin;
    scrollbar-color: #4b5563 #1f2937;
    }
</style>