<script setup lang="ts">
    import { onMounted, onUnmounted, watch, ref } from 'vue';
    import { useDetectionsStore } from '@/stores/detections-store';
    import { useStatsStore } from '@/stores/stats-store';
    import { useFramesStore } from '@/stores/frames-store';
    import { useAnalyticsStore } from '@/stores/analytics-store';
    import { useAnomaliesStore } from '@/stores/anomalies-store';
    import StreamInfo from '@/components/StreamInfo.vue';
    import VideoFeed from '@/components/VideoFeed.vue';
    import DetectionsList from '@/components/DetectionsList.vue';
    import AnalyticsList from '@/components/AnalyticsList.vue';
    import Search from '@/components/Search.vue';
    import DevInfo from '@/components/DevInfo.vue';

    const detectionsStore = useDetectionsStore();
    const statsStore = useStatsStore();
    const framesStore = useFramesStore();
    const analyticsStore = useAnalyticsStore();
    const anomaliesStore = useAnomaliesStore();

    const socket = ref<WebSocket | null>(null);

    onMounted(() => {
        //Initialize socket connection with backend
        socket.value = new WebSocket("ws://localhost:8000/updates");
        socket.value.onopen = () => {
            console.log("Connected to Drone Inference Server");
        };

        let fetchingAnomalies = false;

        socket.value.onmessage = (event) => {
            const data = JSON.parse(event.data);
            switch (data.type) {
                // Fetch frame
                case "NEW_FRAME":
                    framesStore.getNewFrame()
                    break

                // Fetch detections / stats data
                case "NEW_DATA":
                    detectionsStore.fetchDetections()
                    statsStore.fetchStats()
                    break

                // Update anomaly list (if check prevents race condition if many anomalies are detected at once)
                case "NEW_ANOMALY":
                    if (!fetchingAnomalies) {
                        fetchingAnomalies = true
                        anomaliesStore.fetchAnomalies().finally(() => {
                            fetchingAnomalies = false
                        })
                    }
                    break
            }
        };

        socket.value.onerror = (error) => console.error("Socket Error:", error);
        socket.value.onclose = () => console.log("Socket Closed");
    })

    watch(
        () => detectionsStore.detections,
        () => {
            analyticsStore.updateDetections();
        },
        { deep: true }
    );

    onUnmounted(() => {
        if (socket.value) {
            socket.value.close();
        }
    })

</script>

<template>
  <div class="flex flex-col md:flex-row gap-6 md:h-screen md:overflow-hidden bg-slate-900">
    
    <div class="flex flex-col gap-6 md:basis-[42%] shrink-0 p-4 min-w-0 md:overflow-y-auto detections-scroll">
        <StreamInfo/>
        <VideoFeed/>
        <AnalyticsList/>
    </div>
    
    <div class="flex flex-col gap-6 bg-slate-950 flex-1 min-w-0 h-screen max-h-screen overflow-hidden">
        <DetectionsList class="shrink-0" />
        <Search class="flex-1 min-h-0" /> 
    </div>

  </div>
</template>