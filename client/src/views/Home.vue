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
  <div class="flex flex-col md:flex-row gap-6 md:h-screen md:overflow-hidden bg-slate-900">
    
    <div class="flex flex-col gap-6 w-full md:basis-[42%] items-center p-4 min-w-0 md:overflow-y-auto detections-scroll">
      <StreamInfo/>
      <VideoFeed/>
      <AnalyticsList/>
    </div>
    
    <div class="bg-slate-950 flex-1 h-auto md:h-full min-h-[500px]">
      <DetectionsList/>
    </div>

  </div>
</template>