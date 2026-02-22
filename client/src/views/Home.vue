<script setup lang="ts">
    import { onMounted, onUnmounted, watch } from 'vue';
    import { useDetectionsStore } from '@/stores/detections-store';
    import { useStatsStore } from '@/stores/stats-store';
    import { useFramesStore } from '@/stores/frames-store';
    import { useAnalyticsStore } from '@/stores/analytics-store';
    import StreamInfo from '@/components/StreamInfo.vue';
    import VideoFeed from '@/components/VideoFeed.vue';
    import DetectionsList from '@/components/DetectionsList.vue';
    import AnalyticsList from '@/components/AnalyticsList.vue';
    import DevInfo from '@/components/DevInfo.vue';

    const detectionsStore = useDetectionsStore();
    const statsStore = useStatsStore();
    const framesStore = useFramesStore();
    const analyticsStore = useAnalyticsStore();

    onMounted(() => {
        detectionsStore.startPolling(200);
        statsStore.startPolling(200);
        framesStore.startPolling(50);
    })

    watch(
        () => detectionsStore.detections,
        () => {
            analyticsStore.updateDetections();
        },
        { deep: true }
    );

    onUnmounted(() => {
        detectionsStore.stopPolling();
        statsStore.stopPolling();
        framesStore.stopPolling();
    })

</script>

<template>
    <div class="flex flex-row gap-6 flex-1 min-h-0">
        <div class="flex flex-col gap-6 basis-[42%] items-center m-4 overflow-y-auto min-w-0">
            <StreamInfo/>
            <VideoFeed/>
            <AnalyticsList/>
        </div>
        
        <div class="bg-slate-950 flex-1 h-full overflow-hidden">
            <DetectionsList/>
        </div>
    </div>
</template>