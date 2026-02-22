<script setup lang="ts">
    import { computed } from 'vue';
    import type { Detection } from '@/services/types';
    import { Crosshair, TriangleAlert } from 'lucide-vue-next';
    import { useAnalyticsStore } from '@/stores/analytics-store';

    const analyticsStore = useAnalyticsStore();

    interface Props {
        detect: Detection
        numDetects: number
    }

    const props = defineProps<Props>();
    const confidence = computed(() =>
        Number((props.detect.confidence * 100).toFixed(2))
    );
    const detectFreqByType = computed(() => {
        if(props.detect.is_anomaly) {
            return analyticsStore.getFrequencyFromList(analyticsStore.anomalyFrequencyByAnomalies, props.detect.class_id)
        }
        else {
            return analyticsStore.getFrequencyFromList(analyticsStore.objectFrequencyByObjects, props.detect.class_id)
        }
    })

    const detectFreqByDetects = computed(() => {
        if(props.detect.is_anomaly) {
            return analyticsStore.getFrequencyFromList(analyticsStore.anomalyFrequencyByDetections, props.detect.class_id)
        }
        else {
            return analyticsStore.getFrequencyFromList(analyticsStore.objectFrequencyByDetections, props.detect.class_id)
        }
    })

</script>

<template>
    <div v-if="detect.is_anomaly" class="m-2 p-2 gap-1 w-auto h-auto bg-gray-900 rounded-sm flex flex-col items-center border border-rose-800 hover:border-red-500">
        <div class="flex flex-row items-center gap-1">
            <TriangleAlert :size="25" class="pr-1 text-red-500" />
            <div class="text-2xl text-red-400 font-tektur">
                {{ detect.class_name }}
            </div>
        </div>
        
        <div class="text-sm">
            <span class="font-orbit text-gray-400">Seen: </span><span class="font-tektur text-red-500 font-semibold">{{ numDetects }}</span>
        </div>
        <div class="w-full h-0.5 bg-rose-800">
        </div>
        <div class="p-2 flex flex-col rounded-b-sm gap-2">
            <div class="text-gray-400 text-xs font-orbit">
                Highest Confidence: 
                <span class="text-red-500 font-tektur font-semibold text-sm">
                    {{ confidence }}%
                </span>
            </div>
            <div class="text-gray-400 text-xs font-orbit">
                <span class="text-red-500 font-tektur font-semibold text-sm">{{ detectFreqByType }}%</span>  of all anomalies are of class <span class="text-red-400">{{ detect.class_name }}</span>.
            </div>
            <div class="text-gray-400 text-xs font-orbit">
                <span class="text-red-500 font-tektur font-semibold text-sm">{{ detectFreqByDetects }}%</span>  of all detections are of class <span class="text-red-400">{{ detect.class_name }}</span>.
            </div>
        </div>
    </div>

    <div v-else class="m-2 p-2 gap-1 w-auto h-auto bg-gray-900 rounded-sm flex flex-col items-center border border-emerald-700 hover:border-lime-600">
        <div class="flex flex-row items-center gap-1">
            <Crosshair :size="25" class="pr-1 text-lime-600" />
            <div class="text-2xl text-lime-400 font-tektur">
                {{ detect.class_name }}
            </div>
        </div>
        <div class="text-sm">
            <span class="font-orbit text-gray-400">Seen: </span><span class="font-tektur text-lime-600 font-semibold">{{ numDetects }}</span>
        </div>
        <div class="w-full h-0.5 bg-emerald-700">
        </div>
        <div class="p-2 flex flex-col rounded-b-sm gap-2">
            <div class="text-gray-400 text-xs font-orbit">
                Highest Confidence: 
                <span class="text-lime-600 font-tektur font-semibold text-sm">
                    {{ confidence }}%
                </span>
            </div>
            <div class="text-gray-400 text-xs font-orbit">
                <span class="text-lime-600 font-tektur font-semibold text-sm">{{ detectFreqByType }}%</span>  of all objects are of class <span class="text-lime-400">{{ detect.class_name }}</span>.
            </div>
            <div class="text-gray-400 text-xs font-orbit">
                <span class="text-lime-600 font-tektur font-semibold text-sm">{{ detectFreqByDetects }}%</span>  of all detections are of class <span class="text-lime-400">{{ detect.class_name }}</span>.
            </div>
        </div>
    </div>
</template>