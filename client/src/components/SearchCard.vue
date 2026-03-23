<script setup lang="ts">
    import type { Anomaly } from '@/services/types';
    import { ref, computed, watch } from 'vue';
    import { useExportStore } from '@/stores/export-store';

    interface Props {
        anomaly: Anomaly
    }
    const props = defineProps<Props>();
    const exportStore = useExportStore();
    const confidence = computed(() =>
        Number((props.anomaly.confidence * 100).toFixed(2))
    );
    const isSelected = ref(false);

    const toggleSelected = () => {
        isSelected.value = !isSelected.value;
        if(isSelected.value) {
            exportStore.selectAnomaly(props.anomaly);
        } else {
            exportStore.deselectAnomaly(props.anomaly.track_id ?? 0);
        }
    }

    watch(
        () => exportStore.selectAllFlag,
        (val) => {
            isSelected.value = val;
        }
    );
</script>

<template>
    <button 
        @click="toggleSelected"
        :class="isSelected ? 'border-red-500 hover:border-red-500' : 'border-gray-600 hover:border-rose-800'"
        class="flex flex-col items-center justify-between p-2 m-2 w-auto h-auto border rounded-sm cursor-pointer"
    >
        <div class="flex flex-row gap-2 items-center">
            <div class="text-3xl text-red-500 font-semibold font-tektur">
                {{ anomaly.track_id }}
            </div>
        </div>
        <div class="w-full h-0.5 bg-rose-800 mt-2"></div>
        <div class="p-2 flex flex-col rounded-b-sm gap-2">
            <div class="text-gray-400 text-sm font-orbit">
                Class: 
                <span class="text-red-400 font-tektur text-sm">
                    {{ anomaly.class_name }}
                </span>
            </div>
            <div class="text-gray-400 text-sm font-orbit">
                Confidence: 
                <span class="text-red-500 font-tektur font-semibold text-sm">
                    {{ confidence }}%
                </span>
            </div>
        </div>
    </button>
</template>