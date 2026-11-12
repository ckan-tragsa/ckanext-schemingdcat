document.addEventListener('DOMContentLoaded', (event) => {
    // Obtén todos los elementos <pre><code>
    const codeBlocks = document.querySelectorAll('pre > code');

    // Itera sobre cada bloque de código
    codeBlocks.forEach((block) => {
        // Usa highlight.js para resaltar la sintaxis
        hljs.highlightBlock(block);
    });
});