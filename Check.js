(function() {
    // 获取当前域名
    const domain = window.location.hostname;
    // 白名单域名
    const allowDomains = ["t8000x.top", "admin.t8000x.top"];
    // 域名不匹配时
    if (!allowDomains.includes(domain)) {
        // 清空整个页面
        document.documentElement.innerHTML = "<title>403 Forbidden</title><h1>Hello Tourist！</h1><i>Current DNS mismatch</i>";
        // 阻止后续代码执行
        throw new Error("网页失效");
    }
})();