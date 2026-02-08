<script setup lang="ts">
    import { useDetectionsStore } from '@/stores/detections-store';
    import StreamInfoBox from './StreamInfoBox.vue';

    const detectionsStore = useDetectionsStore();

</script>

<template>
    <div class="mt-4 flex gap-6 items-center w-full bg-gray-800">
        <StreamInfoBox
            :num="detectionsStore.num_detections ?? 0";
            label="Objects Detected"
            :iconSelect="1"
        />
        <StreamInfoBox
            :num="detectionsStore.anomaly_count ?? 0";
            label="Anomalies Detected"
            :iconSelect="2"
        />
        <StreamInfoBox
            :num="detectionsStore.inference_fps ?? 0";
            label="FPS"
            :iconSelect="3"
        />
        <StreamInfoBox
            :num="detectionsStore.inference_count ?? 0";
            label="Inferences"
            :iconSelect="4"
        />
    </div>
    
</template>