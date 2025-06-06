<template>
  <router-view/>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
#app{
  height: 100%;
  display: flex;
  width: 100%;
  min-height: 100vh;
  background-color: #f0f0f0;
  margin: 0;
  padding: 0;
}
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  line-height: 1.6;
  color: #333;
}

</style>