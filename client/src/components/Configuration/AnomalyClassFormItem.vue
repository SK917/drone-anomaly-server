<script setup lang="ts">
    import { useAnomaliesStore } from '@/stores/anomalies-store';
    import { SquareCheckBig, Square } from 'lucide-vue-next';
    import { computed, watch } from 'vue';

    const anomaliesStore = useAnomaliesStore();

    interface Props {
        id: number
    }
    const props = defineProps<Props>();

    const toggle = () => {
        anomaliesStore.updateClassSelectStatus(props.id);
    }

    const classItem = computed(() =>
        anomaliesStore.selectedClasses.find(s => s.class_id === props.id)
    );

</script>

<template>
    <button 
        @click="toggle"
        :class="[
            classItem?.selected ? 'text-red-400' : 'text-lime-400'
        ]"
        class="flex flex-row items-center gap-2 font-orbit text-md cursor-pointer"
    >
        <SquareCheckBig v-if="classItem?.selected" :size="24" class="text-red-500"/>
        <Square v-else :size="24" class="text-gray-400"/>
        {{ classItem?.class_name }}
    </button>
</template>