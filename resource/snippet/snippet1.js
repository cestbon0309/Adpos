const resizeOb= new ResizeObserver(entries => {
    for(const entry of entries) {
        var j = {};
        j.tag = "e8fa9d";
        j.src = entry.target.src;
        j.width = entry.target.width;
        j.height = entry.target.height;
        console.log(JSON.stringify(j));
    }
});

elements = document.getElementsByTagName("img")
for(let i=0; i<elements.length; i++)
    resizeOb.observe(elements[i])