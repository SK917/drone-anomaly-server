<script setup lang="ts">
    import { ref } from 'vue';
    import { useDetectionsStore } from '@/stores/detections-store';
    import type { Detection, DetectionsResponse } from '@/services/types';
    import DetectionCard from './DetectionCard.vue';
    import { RefreshCw } from 'lucide-vue-next';

    const detectionsStore = useDetectionsStore();
    const anomaliesOnly = ref(false);

    const toggleAnomalies = () => {
        anomaliesOnly.value = !anomaliesOnly.value;
    }

</script>

<template>
    <div class="flex flex-col items-end">
        <div class="flex flex-row w-full mt-4" >
            <div class="mr-4 ml-4 mb-4">
                <button 
                    @click="toggleAnomalies"
                    class="flex flex-row gap-3 items-center cursor-pointer bg-gray-800 rounded-sm p-2 text-gray-400 border border-transparent
                    hover:border-yellow-600 hover:text-white font-orbit text-xs"
                >
                    <RefreshCw :size=20 class="text-amber-200"/>
                    {{ anomaliesOnly ? 'Show All Detections' : 'Show Anomalies Only'}}
                </button>
            </div>
        </div>
        <div class="ml-4 mr-4 w-[calc(100%-2rem)] h-130 bg-gray-800 rounded-sm p-2 overflow-y-auto detections-scroll">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-1 content-start">
                <div v-if="detectionsStore.groupedDetectionsSorted.length===0" 
                    class="col-span-1 md:col-span-2 lg:col-span-3 h-full flex items-center justify-center text-gray-400 text-lg font-orbit">
                    No detections.
                </div>
                
                <DetectionCard
                    v-else
                    v-for="item in (
                        anomaliesOnly
                        ? detectionsStore.groupedAnomalies
                        : detectionsStore.groupedDetectionsSorted
                    )"
                    :key="item.detection.class_id"
                    :detect="item.detection"
                    :numDetects="item.numDetects"
                />
            </div>
        </div>
    </div>
    
</template>