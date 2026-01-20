<script setup lang="ts">
    import { useStatsStore } from '@/stores/stats-store';

    const statsStore = useStatsStore();

</script>

<template>
    <div class="m-4 ml-12">
        <div class="text-gray-400 text-md pb-4">
            Development Information:
        </div>
        <div class="text-gray-400 text-md">
            has_stream: {{ statsStore.has_stream }}
        </div>
        <div class="text-gray-400 text-md">
            is_processing: {{ statsStore.is_processing }}
        </div>
    </div>
</template>