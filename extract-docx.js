const mammoth = require("mammoth");
const fs = require("fs");

mammoth.convertToHtml({path: "TM5 Coupa Treasury Automatisierung Arbeitsanweisung.docx"})
    .then(function(result){
        const html = result.value;
        fs.writeFileSync("output.html", html);
        console.log(html);
    })
    .catch(function(err){
        console.error(err);
    });
