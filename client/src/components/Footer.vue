<script setup lang="ts">
    const teamMembers = import.meta.env.VITE_TEAM_MEMBERS || "";
</script>

<template>
    <footer class="bg-gray-950 p-3 text-xs text-gray-200 flex justify-between items-center gap-4 font-orbit border-t border-t-yellow-600">
        <div>
            NG-06 TMU Engineering Capstone
        </div>
        <div class="text-right">
            {{ teamMembers }}
        </div>
    </footer>
</template>