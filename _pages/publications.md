---
layout: page
permalink: /publications/
title: publications
description: '†: authors who contributed equally.'
nav: true
nav_order: 1
---
<!-- _pages/publications.md -->
<div class="publications">


<h1>Preprints</h1>
<!--<h2>Preprints</h2>-->

{% bibliography -f {{ site.scholar.bibliography }} --group_by none --query @*[keywords=preprint]* %}

<div style="margin-top: 2em;"></div>


<h1>Peer-reviewed journals</h1>
<!--<h2>Peer-reviewed journals</h2>-->



{% bibliography -f {{ site.scholar.bibliography }} --query @*[keywords=publication]* %}


</div>
