<script setup lang="ts">
    interface Props {
        label: String
        isFirst: boolean
        isSubHeader: boolean
    }

    const props = defineProps<Props>();

</script>

<template>
    <div v-if="isFirst" class="text-2xl text-white font-bold text-center p-2">
        {{ label }}
    </div>
    <div v-else-if="isSubHeader" class="text-xl text-gray-400 p-2">
        {{ label }}
    </div>
    <div v-else class="text-2xl text-white font-bold text-center m-2 pt-4 border-t border-t-amber-200">
        {{ label }}
    </div>
</template>