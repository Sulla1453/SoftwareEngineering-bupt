<template>
  <router-view/>
</template>

<script>
export default {
  name: 'App',
  mounted(){
    document.body.style.zoom = 2 / window.devicePixelRatio;
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
html, body{
  width: 100%;
  height: 100%;
}
html, body, div, span, h1, h2, h3, h4, h5, h6 {
  margin: 0;
  padding: 0;
}
#app{
  height: 100%;
  display: flex;
  width: 100vw;
  min-height: 100vh;
  background-color: #f0f0f0;
  margin: 0;
  padding: 0;
  flex-direction: column;
}


body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  width: 100%;
  color: #333;
}

</style>