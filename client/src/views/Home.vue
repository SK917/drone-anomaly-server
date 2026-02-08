<script setup lang="ts">
    import { onMounted, onUnmounted, watch } from 'vue';
    import { useDetectionsStore } from '@/stores/detections-store';
    import { useStatsStore } from '@/stores/stats-store';
    import { useFramesStore } from '@/stores/frames-store';
    import { useAnalyticsStore } from '@/stores/analytics-store';
    import StreamInfo from '@/components/StreamInfo.vue';
    import VideoFeed from '@/components/VideoFeed.vue';
    import DetectionsList from '@/components/DetectionsList.vue';
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
    <div class="flex flex-col gap-6">
        <div>
            <StreamInfo/>
        </div>
        <div class="flex flex-row gap-20">
            <div class="flex flex-col gap-6">
                <VideoFeed/>
                <DevInfo/>
            </div>
            <div>
                <DetectionsList/>
            </div>
        </div>
    </div>
</template>