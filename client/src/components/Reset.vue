<script setup lang="ts">
    import { ref, computed } from 'vue';
    import { useSocketStore } from '@/stores/socket-store';
    import { useAnomaliesStore } from '@/stores/anomalies-store';
    import { useDetectionsStore } from '@/stores/detections-store';
    import { useExportStore } from '@/stores/export-store';
    import { useAnalyticsStore } from '@/stores/analytics-store';
    import { Trash, X } from 'lucide-vue-next';
    import AnomalyClassFormItem from './AnomalyClassFormItem.vue';

    const socketStore = useSocketStore();
    const anomaliesStore = useAnomaliesStore();
    const detectionsStore = useDetectionsStore();
    const exportStore = useExportStore();
    const analyticsStore = useAnalyticsStore();
    const viewSettingsPopup = ref(false);

    const standardClasses = computed(() => 
        anomaliesStore.selectedClasses.filter(item => !item.suggested_as_anomaly)
    );

    const anomalyClasses = computed(() => 
        anomaliesStore.selectedClasses.filter(item => item.suggested_as_anomaly)
    );

    const toggleResetPopup = () => {
        viewSettingsPopup.value = !viewSettingsPopup.value;
    }

    const reset = () => {
        socketStore.send({
            type: "RESET"
        })

        anomaliesStore.resetAnomalies();
        detectionsStore.resetCounts();
        exportStore.resetExportRequest();
        analyticsStore.resetAnalytics();

        toggleResetPopup();
    }

</script>

<template>
    <button 
        @click="toggleResetPopup"
        class="flex flex-row gap-3 w-20 items-center cursor-pointer bg-gray-800 rounded-sm p-2 text-gray-400 border border-transparent
        hover:border-yellow-600 hover:text-white font-orbit text-xs"
    >
        <Trash :size=20 class="text-amber-200"/>
        Reset
    </button>

    <Teleport to="body">
        <div
            v-show="viewSettingsPopup"
            class="fixed inset-0 z-100 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm"
        >
            <div class="bg-gray-900 border-2 border-gray-600 p-4 rounded-lg shadow-2xl max-w-lg w-full max-h-[95vh] m-2 flex flex-col gap-1 font-tektur overflow-y-auto detections-scroll">
                <div class="flex flex-row justify-end">
                    <button
                        @click="toggleResetPopup"
                        class="cursor-pointer text-gray-400 hover:text-amber-200 rounded-sm p-1"
                    >
                        <X :size=30 />
                    </button>
                </div>
                <div class="flex flex-col gap-2">
                    <div class="text-center text-3xl text-amber-200 uppercase">Warning</div>
                    <div class="text-center text-lg text-gray-400">This will reset <span class="text-red-500 font-bold">all</span> data!</div>
                    <div class="text-center text-lg text-gray-400">If you're sure, select <span class="text-yellow-600 font-bold">Confirm</span> below.</div>
                </div>
                
                <button
                    @click="reset"
                    class="w-full bg-gray-800 text-gray-400 border border-transparent text-xl font-bold py-2 mt-6 rounded uppercase hover:border-amber-200 hover:text-gray-200 cursor-pointer"
                >
                    Confirm
                </button>
            </div>

        </div>
    </Teleport>
</template>