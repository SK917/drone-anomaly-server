<script setup lang="ts">
    import { useExportStore } from '@/stores/export-store';
    import { useAnomaliesStore } from '@/stores/anomalies-store';
    import type { ExportRequest } from '@/services/types';
    import { SquareCheckBig, Square } from 'lucide-vue-next';
    import { computed, watch } from 'vue';

    const exportStore = useExportStore();
    const anomaliesStore = useAnomaliesStore();

    interface Props {
        field: keyof ExportRequest;
        label: string;
    }

    const props = defineProps<Props>();

    const isDisabled = computed(() =>
        props.field === 'selected_anomalies' && exportStore.selectedAnomalies.length === 0
    );

    const isDisabledAll = computed(() =>
        props.field === 'all_anomalies' && anomaliesStore.anomalies.length === 0
    );  

    watch(isDisabled, (val) => {
        if (val && exportStore.exportRequest.selected_anomalies) {
            exportStore.updateExportRequest('selected_anomalies', false);
        }
    });

    watch(isDisabledAll, (val) => {
        if (val && exportStore.exportRequest.all_anomalies) {
            exportStore.updateExportRequest('all_anomalies', false);
        }
    });

    const toggle = () => {
        if (isDisabled.value || isDisabledAll.value) return;
        const current = exportStore.exportRequest[props.field];
        exportStore.updateExportRequest(props.field, !current);
    }

    const isRowDisabled = computed(() => isDisabled.value || isDisabledAll.value);

</script>

<template>
    <button 
        @click="toggle"
        :class="[
            isRowDisabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer hover:text-gray-200',
            exportStore.exportRequest[field] ? 'text-gray-200' : 'text-gray-400'
        ]"
        class="flex flex-row items-center gap-2 font-orbit text-md"
    >
        <SquareCheckBig v-if="exportStore.exportRequest[field]" :size="24" class="text-amber-200"/>
        <Square v-else :size="24" class="text-gray-400"/>
        {{ label }}
    </button>
</template>