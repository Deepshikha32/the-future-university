import http.server
import socketserver
import json
import os
import urllib.parse
import sys
import re
import base64
from typing import Dict, Any, List

from research_agent.config import AgentConfig
from research_agent.brief_generator import ResearchAgent
from research_agent.document_loader import DocumentLoader

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKS_DIR = os.path.join(BASE_DIR, "packs")

os.makedirs(os.path.join(PACKS_DIR, "SRVCABLE"), exist_ok=True)

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Equity Research Intelligence · Placement Drive</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --navy:      #0d1b2a;
            --navy-mid:  #0f2235;
            --navy-card: #142840;
            --navy-hover:#1a3252;
            --teal:      #00c9a7;
            --teal-dim:  rgba(0,201,167,0.14);
            --teal-glow: rgba(0,201,167,0.3);
            --blue:      #4a9eff;
            --blue-dim:  rgba(74,158,255,0.14);
            --green:     #34d399;
            --amber:     #fbbf24;
            --rose:      #fb7185;
            --text:      #ddeeff;
            --muted:     #6a90b0;
            --border:    rgba(255,255,255,0.07);
            --border-hi: rgba(0,201,167,0.4);
            --r-lg: 14px;
            --r-md: 9px;
            --r-sm: 6px;
        }
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}

        body {
            font-family:'Inter',-apple-system,sans-serif;
            background:var(--navy);
            color:var(--text);
            min-height:100vh;
            display:flex;
            flex-direction:column;
        }

        /* ── Top Bar ── */
        .topbar{
            height:50px;display:flex;align-items:center;
            justify-content:space-between;padding:0 28px;
            background:var(--navy-mid);border-bottom:1px solid var(--border);
            flex-shrink:0;
        }
        .topbar-left{display:flex;align-items:center;gap:14px;}
        .topbar-logo{
            font-size:11px;font-weight:800;letter-spacing:1.4px;
            text-transform:uppercase;color:var(--teal);
        }
        .topbar-sep{width:1px;height:18px;background:var(--border);}
        .topbar-sub{font-size:11.5px;color:var(--muted);font-weight:500;}
        .live-badge{
            display:inline-flex;align-items:center;gap:7px;
            background:rgba(52,211,153,0.09);border:1px solid rgba(52,211,153,0.22);
            color:var(--green);font-size:11px;font-weight:600;
            padding:4px 12px;border-radius:30px;
        }
        .live-dot{
            width:6px;height:6px;border-radius:50%;background:var(--green);
            animation:pulse 1.8s infinite;
        }
        @keyframes pulse{
            0%{box-shadow:0 0 0 0 rgba(52,211,153,.7);}
            70%{box-shadow:0 0 0 7px rgba(52,211,153,0);}
            100%{box-shadow:0 0 0 0 rgba(52,211,153,0);}
        }

        /* ── Shell ── */
        .shell{flex:1;display:flex;overflow:hidden;min-height:0;}

        /* ── Sidebar ── */
        .sidebar{
            width:252px;flex-shrink:0;
            background:var(--navy-mid);border-right:1px solid var(--border);
            display:flex;flex-direction:column;
            overflow-y:auto;padding:18px 14px 28px;gap:4px;
        }
        .sidebar::-webkit-scrollbar{width:3px;}
        .sidebar::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1);border-radius:3px;}

        .sb-label{
            font-size:9.5px;font-weight:800;letter-spacing:1.4px;
            text-transform:uppercase;color:var(--muted);
            padding:14px 2px 7px;
        }

        /* Ticker input */
        .sb-input{
            width:100%;padding:9px 11px;
            background:var(--navy-card);border:1px solid var(--border);
            border-radius:var(--r-md);color:var(--text);
            font-family:'JetBrains Mono',monospace;font-size:13.5px;
            font-weight:700;letter-spacing:.6px;text-transform:uppercase;
            outline:none;transition:border-color .2s,box-shadow .2s;
            margin-bottom:10px;
        }
        .sb-input:focus{border-color:var(--teal);box-shadow:0 0 0 3px var(--teal-glow);}

        /* Date row */
        .date-row{display:flex;gap:5px;align-items:center;margin-bottom:7px;}
        .date-row input[type=date]{
            flex:1;padding:7px 9px;background:var(--navy-card);
            border:1px solid var(--border);border-radius:var(--r-md);
            color:var(--text);font-size:12.5px;outline:none;
            color-scheme:dark;transition:border-color .2s;
        }
        .date-row input[type=date]:focus{border-color:var(--teal);}
        .btn-cal{
            padding:7px 9px;background:var(--navy-card);
            border:1px solid var(--border);border-radius:var(--r-md);
            color:var(--muted);cursor:pointer;font-size:14px;
            transition:all .15s;flex-shrink:0;
        }
        .btn-cal:hover{border-color:var(--teal);color:var(--teal);}

        /* Date chips */
        .chips{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:14px;}
        .chip{
            padding:3px 8px;font-size:10.5px;font-weight:600;
            border-radius:20px;background:rgba(255,255,255,.05);
            border:1px solid var(--border);color:var(--muted);
            cursor:pointer;transition:all .15s;
        }
        .chip:hover{background:var(--teal-dim);color:var(--teal);border-color:var(--border-hi);}

        /* Generate button */
        .btn-gen{
            width:100%;padding:11px;background:var(--teal);
            border:none;border-radius:var(--r-md);
            color:#08161f;font-weight:800;font-size:13px;
            cursor:pointer;display:flex;align-items:center;
            justify-content:center;gap:7px;
            transition:all .2s;margin-bottom:6px;
            box-shadow:0 4px 18px rgba(0,201,167,.28);
            letter-spacing:.2px;
        }
        .btn-gen:hover{background:#00ddb8;box-shadow:0 6px 22px rgba(0,201,167,.42);transform:translateY(-1px);}
        .btn-gen:active{transform:translateY(0);}
        .btn-gen:disabled{opacity:.55;cursor:not-allowed;transform:none;}

        /* Upload zone */
        .upload-zone{
            border:1.5px dashed rgba(0,201,167,.3);
            border-radius:var(--r-md);background:rgba(0,201,167,.03);
            padding:14px 10px;display:flex;flex-direction:column;
            align-items:center;gap:5px;cursor:pointer;
            transition:all .2s;margin-bottom:10px;
        }
        .upload-zone:hover,.upload-zone.drag-over{
            background:rgba(0,201,167,.09);border-color:var(--teal);
        }
        .upload-icon{font-size:20px;}
        .upload-lbl{font-size:12px;font-weight:700;color:var(--teal);}
        .upload-hint{font-size:10px;color:var(--muted);}

        /* Doc count */
        .doc-row{
            display:flex;align-items:center;justify-content:space-between;
            font-size:11px;color:var(--muted);margin-bottom:8px;
        }
        .count-pill{
            background:var(--teal-dim);color:var(--teal);
            font-size:10.5px;font-weight:700;
            padding:2px 9px;border-radius:20px;
            border:1px solid rgba(0,201,167,.22);
        }

        /* Doc list */
        .doc-list{display:flex;flex-direction:column;gap:4px;max-height:230px;overflow-y:auto;}
        .doc-list::-webkit-scrollbar{width:3px;}
        .doc-list::-webkit-scrollbar-thumb{background:rgba(255,255,255,.08);border-radius:3px;}
        .doc-item{
            display:flex;align-items:center;gap:7px;
            padding:7px 9px;background:var(--navy-card);
            border:1px solid var(--border);border-radius:var(--r-sm);
            font-size:11.5px;transition:all .15s;
        }
        .doc-item:hover{border-color:var(--border-hi);background:var(--navy-hover);}
        .doc-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#c0d8ee;font-weight:500;}
        .doc-tier{font-size:9.5px;font-weight:700;padding:1px 5px;border-radius:8px;flex-shrink:0;}
        .t1{background:rgba(52,211,153,.12);color:var(--green);border:1px solid rgba(52,211,153,.22);}
        .t2{background:rgba(74,158,255,.12);color:var(--blue);border:1px solid rgba(74,158,255,.22);}
        .t3{background:rgba(251,191,36,.12);color:var(--amber);border:1px solid rgba(251,191,36,.22);}
        .btn-del{
            background:transparent;border:none;color:var(--muted);
            cursor:pointer;padding:2px 4px;border-radius:4px;
            font-size:11px;flex-shrink:0;transition:all .15s;
        }
        .btn-del:hover{color:var(--rose);background:rgba(251,113,133,.12);}

        /* ── Main Panel ── */
        .main{flex:1;display:flex;flex-direction:column;overflow-y:auto;min-width:0;}
        .main::-webkit-scrollbar{width:4px;}
        .main::-webkit-scrollbar-thumb{background:rgba(255,255,255,.09);border-radius:4px;}

        /* Hero */
        .hero{padding:44px 52px 34px;border-bottom:1px solid var(--border);}
        .hero-eyebrow{
            font-size:10.5px;font-weight:700;letter-spacing:2px;
            text-transform:uppercase;color:var(--teal);margin-bottom:16px;
        }
        .hero-eyebrow em{color:var(--muted);font-style:normal;margin:0 6px;}
        .hero-h1{
            font-size:38px;font-weight:800;letter-spacing:-1px;
            color:#fff;line-height:1.12;margin-bottom:14px;
        }
        .hero-sub{
            font-size:14px;color:var(--muted);
            max-width:580px;line-height:1.75;margin-bottom:22px;
        }
        .hero-tags{display:flex;gap:9px;flex-wrap:wrap;}
        .hero-tag{
            display:inline-flex;align-items:center;gap:5px;
            padding:5px 14px;border-radius:30px;
            font-size:11.5px;font-weight:600;border:1px solid;
        }
        .tag-teal{background:rgba(0,201,167,.1);color:var(--teal);border-color:rgba(0,201,167,.28);}
        .tag-blue{background:var(--blue-dim);color:var(--blue);border-color:rgba(74,158,255,.28);}
        .tag-amber{background:rgba(251,191,36,.1);color:var(--amber);border-color:rgba(251,191,36,.28);}

        /* KPI strip */
        .kpi-strip{
            display:grid;grid-template-columns:repeat(4,1fr);
            gap:14px;padding:24px 52px;border-bottom:1px solid var(--border);
        }
        .kpi-card{
            background:var(--navy-card);border:1px solid var(--border);
            border-radius:var(--r-lg);padding:18px 20px;transition:all .2s;
        }
        .kpi-card:hover{border-color:var(--border-hi);transform:translateY(-2px);}
        .kpi-lbl{font-size:11px;color:var(--muted);font-weight:500;margin-bottom:8px;}
        .kpi-val{
            font-size:28px;font-weight:800;color:#fff;
            letter-spacing:-.5px;font-family:'JetBrains Mono',monospace;
        }
        .kpi-delta{
            font-size:11px;font-weight:600;margin-top:7px;
            padding:2px 8px;border-radius:10px;display:inline-block;
        }
        .up{background:rgba(52,211,153,.12);color:var(--green);}
        .neutral{background:rgba(74,158,255,.12);color:var(--blue);}
        .dn{background:rgba(251,113,133,.12);color:var(--rose);}

        /* Content area */
        .content{padding:28px 52px 44px;flex:1;}

        /* Tabs */
        .tabs{display:flex;gap:2px;margin-bottom:24px;border-bottom:1px solid var(--border);}
        .tab-btn{
            background:transparent;border:none;border-bottom:2px solid transparent;
            color:var(--muted);font-size:13px;font-weight:600;
            padding:10px 20px;cursor:pointer;transition:all .2s;
            margin-bottom:-1px;display:flex;align-items:center;gap:7px;
        }
        .tab-btn:hover{color:var(--text);}
        .tab-btn.active{color:var(--teal);border-bottom-color:var(--teal);}
        .tab-pane{display:none;}
        .tab-pane.active{display:block;}

        /* Brief */
        .brief-bar{display:flex;justify-content:flex-end;margin-bottom:14px;}
        .btn-ghost{
            padding:6px 13px;background:rgba(255,255,255,.05);
            border:1px solid var(--border);border-radius:var(--r-sm);
            color:var(--muted);font-size:12px;font-weight:600;
            cursor:pointer;display:inline-flex;align-items:center;gap:6px;
            transition:all .15s;
        }
        .btn-ghost:hover{color:var(--text);border-color:var(--border-hi);background:rgba(0,201,167,.06);}

        .brief-viewer{
            background:var(--navy-card);border:1px solid var(--border);
            border-radius:var(--r-lg);padding:36px 40px;
            line-height:1.8;min-height:380px;
        }
        .brief-viewer h1{font-size:21px;color:#fff;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--border);}
        .brief-viewer h2{font-size:16px;color:#fff;margin:22px 0 9px;}
        .brief-viewer h3{font-size:14.5px;color:var(--teal);margin:18px 0 7px;}
        .brief-viewer p{font-size:13.5px;color:#a8c4dc;margin-bottom:13px;}
        .brief-viewer ul{padding-left:20px;margin-bottom:16px;}
        .brief-viewer li{font-size:13.5px;color:#b8cfe0;margin-bottom:7px;}
        .brief-viewer table{width:100%;border-collapse:collapse;margin:14px 0 20px;font-size:12.5px;}
        .brief-viewer th{background:rgba(255,255,255,.04);color:var(--muted);font-weight:600;padding:9px 13px;text-align:left;border:1px solid var(--border);}
        .brief-viewer td{padding:9px 13px;border:1px solid var(--border);color:#b0c8de;}
        .brief-viewer strong{color:#e8f4ff;}

        /* Charts */
        .charts-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;}
        .chart-card{
            background:var(--navy-card);border:1px solid var(--border);
            border-radius:var(--r-lg);padding:20px;
        }
        .chart-title{font-size:12.5px;font-weight:700;color:var(--text);margin-bottom:14px;display:flex;align-items:center;gap:7px;}
        .chart-box{position:relative;height:250px;}

        /* Empty state */
        .empty{
            display:flex;flex-direction:column;align-items:center;
            justify-content:center;min-height:300px;
            gap:10px;color:var(--muted);text-align:center;
        }
        .empty-icon{font-size:38px;opacity:.4;}
        .empty-title{font-size:15px;font-weight:700;color:var(--text);}
        .empty-sub{font-size:13px;max-width:320px;line-height:1.65;}

        @keyframes spin{to{transform:rotate(360deg);}}
        .spinner{display:inline-block;width:14px;height:14px;border:2px solid rgba(8,22,31,.3);border-top-color:#08161f;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;}

        /* Animated gradient headline */
        @keyframes gradShift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
        .hero-h1-gradient{
            font-size:38px;font-weight:800;letter-spacing:-1px;line-height:1.12;
            margin-bottom:10px;
            background:linear-gradient(120deg,#fff 0%,#00c9a7 35%,#4a9eff 65%,#fff 100%);
            background-size:200% 200%;
            animation:gradShift 5s ease infinite;
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;
        }
        .hero-kicker{
            font-size:11px;font-weight:700;letter-spacing:2px;
            text-transform:uppercase;color:var(--teal);margin-bottom:16px;
            display:flex;align-items:center;gap:8px;
        }
        .hero-kicker::before{content:'';display:inline-block;width:28px;height:2px;background:var(--teal);border-radius:2px;}

        /* Feature pills row */
        .feature-pills{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px;}
        .feat-pill{
            display:inline-flex;align-items:center;gap:6px;
            padding:5px 13px;border-radius:8px;font-size:11.5px;font-weight:600;
            background:rgba(255,255,255,.04);border:1px solid var(--border);color:var(--muted);
            transition:all .2s;
        }
        .feat-pill:hover{background:var(--teal-dim);color:var(--teal);border-color:var(--border-hi);}

        /* Company Overview section (shown after run) */
        .overview-section{padding:26px 52px;border-bottom:1px solid var(--border);display:none;}
        .overview-header{display:flex;align-items:baseline;gap:12px;margin-bottom:16px;}
        .overview-title{font-size:17px;font-weight:700;color:#fff;}
        .overview-sub{font-size:11.5px;color:var(--muted);}
        .stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;}
        .stat-card{
            background:var(--navy-card);border:1px solid var(--border);
            border-radius:var(--r-lg);padding:16px 18px;
            transition:all .2s;position:relative;overflow:hidden;
        }
        .stat-card::before{
            content:'';position:absolute;top:0;left:0;right:0;height:2px;
            background:linear-gradient(90deg,var(--teal),var(--blue));
            opacity:0;transition:opacity .2s;
        }
        .stat-card:hover{border-color:var(--border-hi);transform:translateY(-2px);}
        .stat-card:hover::before{opacity:1;}
        .stat-lbl{font-size:10.5px;color:var(--muted);font-weight:500;margin-bottom:8px;text-transform:uppercase;letter-spacing:.6px;}
        .stat-val{font-size:24px;font-weight:800;color:#fff;letter-spacing:-.5px;font-family:'JetBrains Mono',monospace;margin-bottom:6px;}
        .stat-delta{font-size:10.5px;font-weight:600;padding:2px 7px;border-radius:8px;display:inline-block;}
        .d-up{background:rgba(52,211,153,.12);color:var(--green);}
        .d-dn{background:rgba(251,113,133,.12);color:var(--rose);}
        .d-nt{background:rgba(74,158,255,.12);color:var(--blue);}

        /* Responsive */
        @media(max-width:1080px){
            .kpi-strip{grid-template-columns:repeat(2,1fr);}
            .hero,.kpi-strip,.content{padding-left:28px;padding-right:28px;}
        }
        @media(max-width:780px){
            .shell{flex-direction:column;}
            .sidebar{width:100%;border-right:none;border-bottom:1px solid var(--border);}
            .charts-grid{grid-template-columns:1fr;}
        }
        /* ── Delete Confirmation Modal ── */
        .modal-backdrop{
            display:none;position:fixed;inset:0;
            background:rgba(5,12,22,.75);backdrop-filter:blur(6px);
            z-index:1000;align-items:center;justify-content:center;
        }
        .modal-backdrop.open{display:flex;}
        .modal-box{
            background:#122033;border:1px solid rgba(251,113,133,.25);
            border-radius:16px;padding:28px 30px;
            max-width:380px;width:90%;box-shadow:0 24px 60px rgba(0,0,0,.6);
            animation:modalIn .18s ease;
        }
        @keyframes modalIn{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
        .modal-icon{font-size:32px;margin-bottom:12px;}
        .modal-title{font-size:16px;font-weight:700;color:#fff;margin-bottom:8px;}
        .modal-msg{font-size:13px;color:var(--muted);line-height:1.6;margin-bottom:22px;}
        .modal-msg strong{color:#fb7185;font-weight:600;}
        .modal-btns{display:flex;gap:10px;justify-content:flex-end;}
        .btn-modal-cancel{
            padding:8px 18px;background:rgba(255,255,255,.06);
            border:1px solid var(--border);border-radius:8px;
            color:var(--muted);font-size:13px;font-weight:600;
            cursor:pointer;transition:all .15s;
        }
        .btn-modal-cancel:hover{background:rgba(255,255,255,.1);color:var(--text);}
        .btn-modal-delete{
            padding:8px 18px;background:rgba(251,113,133,.15);
            border:1px solid rgba(251,113,133,.35);border-radius:8px;
            color:#fb7185;font-size:13px;font-weight:700;
            cursor:pointer;transition:all .15s;
            display:inline-flex;align-items:center;gap:6px;
        }
        .btn-modal-delete:hover{background:rgba(251,113,133,.28);border-color:#fb7185;}
    </style>
</head>
<body>

<!-- Custom Delete Confirmation Modal -->
<div class="modal-backdrop" id="deleteModal">
    <div class="modal-box">
        <div class="modal-icon">🗑️</div>
        <div class="modal-title">Delete document?</div>
        <div class="modal-msg">This will permanently remove <strong id="deleteModalFilename">file.md</strong> from the repository. This action cannot be undone.</div>
        <div class="modal-btns">
            <button class="btn-modal-cancel" onclick="closeDeleteModal()">Cancel</button>
            <button class="btn-modal-delete" id="deleteModalConfirm">🗑 Delete</button>
        </div>
    </div>
</div>

<div class="topbar">
    <div class="topbar-left">
        <span class="topbar-logo">Equity Intelligence</span>
        <span class="topbar-sep"></span>
        <span class="topbar-sub">Placement Drive Research Agent</span>
    </div>
    <span class="live-badge"><span class="live-dot"></span>Agent Active</span>
</div>

<div class="shell">

    <!-- Sidebar -->
    <aside class="sidebar" id="dropCard">

        <div class="sb-label">Workspace</div>

        <label style="font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;">NSE Ticker</label>
        <input class="sb-input" type="text" id="tickerInput" value="SRVCABLE"
               placeholder="e.g. SRVCABLE, INFY, TCS"
               oninput="onTickerChange()">

        <label style="font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;">Reference Date</label>
        <div class="date-row">
            <input type="date" id="refDate" value="2026-09-23"
                   onchange="onDateChange()" onclick="try{this.showPicker()}catch(e){}">
            <button class="btn-cal" onclick="try{document.getElementById('refDate').showPicker()}catch(e){}" title="Pick date">📅</button>
        </div>
        <div class="chips">
            <span class="chip" onclick="setDatePreset('2026-09-23')">23 Sep 2026</span>
            <span class="chip" onclick="setDatePreset('today')">Today</span>
            <span class="chip" onclick="setDatePreset('2026-08-11')">Q1 Concall</span>
        </div>

        <button class="btn-gen" id="btnRunAgent" onclick="runAgent()">✦ Generate research brief</button>

        <div class="sb-label">Research Documents</div>

        <div class="upload-zone" id="uploadZone" onclick="triggerDirectUpload()">
            <span class="upload-icon">⬆</span>
            <span class="upload-lbl">Upload</span>
            <span class="upload-hint">PDF · TXT · MD · CSV &nbsp;·&nbsp; select multiple</span>
        </div>
        <input type="file" id="directFileInput" accept=".pdf,.txt,.md,.csv" multiple
               onchange="handleDirectFileSelect(event)" style="display:none;">

        <div class="doc-row">
            <span>Files for <strong id="docsTickerHeader" style="color:var(--teal)">SRVCABLE</strong></span>
            <span class="count-pill" id="quickDocCount">0</span>
        </div>
        <div class="doc-list" id="sidebarDocListContainer">
            <div style="color:var(--muted);font-size:11.5px;text-align:center;padding:12px;">Loading…</div>
        </div>

    </aside>

    <!-- Main panel -->
    <main class="main">

        <!-- Hero -->
        <div class="hero">
            <div class="hero-h1-gradient">Decode the fundamentals.<br>Own the conviction.</div>
            <div class="hero-sub" style="margin-top:14px;">Upload company filings, concall transcripts, and analyst notes — the agent reads every line, cross-checks facts, and delivers a structured investment brief grounded strictly in your documents.</div>
            <div class="hero-tags" style="margin-top:16px;">
                <span class="hero-tag tag-teal">● Document-Grounded</span>
                <span class="hero-tag tag-blue" id="heroTagTicker">NSE: SRVCABLE</span>
                <span class="hero-tag tag-amber" id="heroTagDate">Ref: 23 Sep 2026</span>
            </div>
            <div class="feature-pills">
                <span class="feat-pill">🔒 Injection-Safe Pipeline</span>
                <span class="feat-pill">🧩 Entity Disambiguation</span>
                <span class="feat-pill">📐 Schema Validation</span>
                <span class="feat-pill">📊 Auto Financial Charts</span>
                <span class="feat-pill">📋 Multi-file Upload</span>
            </div>
        </div>

        <!-- Company Overview (shown after run) -->
        <div class="overview-section" id="overviewSection">
            <div class="overview-header">
                <span class="overview-title">Company Overview</span>
                <span class="overview-sub" id="overviewSub">Figures extracted from supplied documents</span>
            </div>
            <div class="stat-grid" id="statGrid">
                <!-- populated by JS -->
            </div>
        </div>

        <!-- KPI cards (shown after run) -->
        <div class="kpi-strip" id="kpiStrip" style="display:none;">
            <div class="kpi-card">
                <div class="kpi-lbl">Documents Loaded</div>
                <div class="kpi-val" id="kpiDocs">—</div>
                <span class="kpi-delta neutral">Processed</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-lbl">Injections Blocked</div>
                <div class="kpi-val" id="kpiSec">—</div>
                <span class="kpi-delta up">Security Pass</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-lbl">Entities Resolved</div>
                <div class="kpi-val" id="kpiEnt">—</div>
                <span class="kpi-delta up">Disambiguated</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-lbl">Validation</div>
                <div class="kpi-val" id="kpiVal">—</div>
                <span class="kpi-delta neutral" id="kpiValTag">Schema Check</span>
            </div>
        </div>

        <!-- Tabs -->
        <div class="content">
            <div class="tabs">
                <button class="tab-btn active" id="tabBtnBrief" onclick="switchTab('brief')">📄 Research Brief</button>
                <button class="tab-btn" id="tabBtnAnalytics" onclick="switchTab('analytics')">📈 Visual Analytics</button>
            </div>

            <div class="tab-pane active" id="viewBrief">
                <div class="brief-bar">
                    <button class="btn-ghost" id="btnCopyBrief" onclick="copyBrief()">📋 Copy to clipboard</button>
                </div>
                <div class="brief-viewer" id="briefContent">
                    <div class="empty">
                        <div class="empty-icon">🔬</div>
                        <div class="empty-title">No brief generated yet</div>
                        <div class="empty-sub">Upload documents in the sidebar, then click <strong style="color:var(--teal)">Generate research brief</strong>.</div>
                    </div>
                </div>
            </div>

            <div class="tab-pane" id="viewAnalytics">
                <div class="charts-grid">
                    <div class="chart-card">
                        <div class="chart-title">📊 Revenue &amp; Net Profitability (&#8377; Cr)</div>
                        <div class="chart-box"><canvas id="chartFinancials"></canvas></div>
                    </div>
                    <div class="chart-card">
                        <div class="chart-title">📉 Margin vs Raw Material Spike</div>
                        <div class="chart-box"><canvas id="chartMargins"></canvas></div>
                    </div>
                    <div class="chart-card">
                        <div class="chart-title">📈 Promoter De-Pledging &amp; Institutional Holdings</div>
                        <div class="chart-box"><canvas id="chartShareholding"></canvas></div>
                    </div>
                    <div class="chart-card">
                        <div class="chart-title">⏳ Working Capital Days vs Order Book</div>
                        <div class="chart-box"><canvas id="chartOperations"></canvas></div>
                    </div>
                </div>
            </div>
        </div>
    </main>
</div>
<script>
    let rawBriefMarkdown = "";
    let chartsInstances = {};

    function getActiveTicker() {
        const val = document.getElementById('tickerInput').value.trim().toUpperCase();
        return val || "SRVCABLE";
    }

    function getActiveDate() {
        const d = document.getElementById('refDate').value;
        return d || "2026-09-23";
    }

    function setDatePreset(preset) {
        const dateInput = document.getElementById('refDate');
        if (preset === 'today') {
            const now = new Date();
            const yyyy = now.getFullYear();
            const mm = String(now.getMonth() + 1).padStart(2, '0');
            const dd = String(now.getDate()).padStart(2, '0');
            dateInput.value = `${yyyy}-${mm}-${dd}`;
        } else {
            dateInput.value = preset;
        }
        onDateChange();
    }

    function switchTab(tabId) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(view => view.classList.remove('active'));

        if (tabId === 'brief') {
            document.getElementById('tabBtnBrief').classList.add('active');
            document.getElementById('viewBrief').classList.add('active');
        } else if (tabId === 'analytics') {
            document.getElementById('tabBtnAnalytics').classList.add('active');
            document.getElementById('viewAnalytics').classList.add('active');
            renderAllCharts();
        }
    }

    function onTickerChange() {
        const ticker = getActiveTicker();
        document.getElementById('docsTickerHeader').innerText = ticker;
        document.getElementById('heroTagTicker').innerText = 'NSE: ' + ticker;
        loadDocumentsList();
    }

    function onDateChange() {
        const d = document.getElementById('refDate').value;
        if (d) {
            const [y,m,day] = d.split('-');
            const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            document.getElementById('heroTagDate').innerText = 'Ref: ' + day + ' ' + months[parseInt(m)-1] + ' ' + y;
        }
    }

    async function loadDocumentsList() {
        const ticker = getActiveTicker();
        try {
            const resp = await fetch(`/api/documents?ticker=${ticker}`);
            const docs = await resp.json();
            
            document.getElementById('quickDocCount').innerText = docs.length;

            const container = document.getElementById('sidebarDocListContainer');
            if (docs.length === 0) {
                container.innerHTML = '<div style="color: var(--text-muted); font-size: 12px; padding: 16px; text-align: center; border: 1.5px dashed var(--border); border-radius: 10px;">No documents yet for ' + ticker + '.<br>Click "Upload Document" above.</div>';
                return;
            }

            let html = '';
            docs.forEach(doc => {
                const tierClass = doc.tier === 1 ? 't1' : (doc.tier === 2 ? 't2' : 't3');
                const tierText = doc.tier === 1 ? 'T1' : (doc.tier === 2 ? 'T2' : 'T3');
                html += `
                <div class="doc-item">
                    <span class="doc-name" title="${doc.filename} (${doc.size_kb} KB)">📄 ${doc.filename}</span>
                    <span class="doc-tier ${tierClass}">${tierText}</span>
                    <button class="btn-del" onclick="deleteDocument('${doc.filename}')" title="Delete">✕</button>
                </div>`;
            });
            container.innerHTML = html;
        } catch (e) {
            console.error("Error loading documents:", e);
        }
    }

    async function runAgent() {
        const btn = document.getElementById('btnRunAgent');
        const ticker = getActiveTicker();
        const refDate = getActiveDate();
        btn.innerHTML = '<span class="spinner"></span> Analysing documents…';
        btn.disabled = true;

        try {
            const resp = await fetch('/api/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker: ticker, reference_date: refDate })
            });
            const res = await resp.json();

            rawBriefMarkdown = res.brief_markdown;
            document.getElementById('briefContent').innerHTML = marked.parse(rawBriefMarkdown);

            // Show and populate KPI strip
            const strip = document.getElementById('kpiStrip');
            strip.style.display = 'grid';
            document.getElementById('kpiDocs').innerText = res.doc_count;
            document.getElementById('kpiSec').innerText = res.injections_blocked;
            document.getElementById('kpiEnt').innerText = res.entity_mismatches_identified;
            document.getElementById('kpiVal').innerText = res.validation_passed ? '✓' : '✗';
            document.getElementById('kpiValTag').className = 'kpi-delta ' + (res.validation_passed ? 'up' : 'dn');
            document.getElementById('kpiValTag').innerText = res.validation_passed ? 'Passed' : 'Failed';

            // Update hero tags
            document.getElementById('heroTagTicker').innerText = 'NSE: ' + res.ticker;

            // Populate Company Overview section from charts_data
            populateOverview(res.ticker, res.charts_data);

            // Store charts data
            window.latestChartsData = res.charts_data;
            renderAllCharts();
            loadDocumentsList();

            switchTab('brief');
        } catch (e) {
            alert('Error running agent: ' + e);
        } finally {
            btn.innerHTML = '✦ Generate research brief';
            btn.disabled = false;
        }
    }

    function populateOverview(ticker, chartsData) {
        const section = document.getElementById('overviewSection');
        const grid = document.getElementById('statGrid');
        const sub = document.getElementById('overviewSub');
        if (!chartsData) return;

        sub.innerText = ticker + ' · Figures extracted from supplied documents';

        // Pull latest values from financial_chart if available
        let stats = [];
        const fc = chartsData.financial_chart;
        if (fc && fc.labels && fc.labels.length > 0) {
            const lastIdx = fc.labels.length - 1;
            const lastLabel = fc.labels[lastIdx];
            fc.datasets.forEach(ds => {
                const val = ds.data[lastIdx];
                if (val == null) return;
                const formatted = val >= 1000
                    ? '₹' + (val/1000).toFixed(1) + 'K Cr'
                    : '₹' + val.toFixed(0) + ' Cr';
                const prev = ds.data[lastIdx - 1];
                let deltaClass = 'd-nt', deltaText = lastLabel;
                if (prev != null && prev !== 0) {
                    const pct = ((val - prev) / Math.abs(prev) * 100).toFixed(1);
                    deltaClass = pct >= 0 ? 'd-up' : 'd-dn';
                    deltaText = (pct >= 0 ? '▲ ' : '▼ ') + Math.abs(pct) + '% YoY';
                }
                stats.push({ lbl: ds.label, val: formatted, deltaClass, deltaText });
            });
        }
        const mc = chartsData.margins_chart;
        if (mc && mc.labels && mc.labels.length > 0) {
            const lastIdx = mc.labels.length - 1;
            mc.datasets.forEach(ds => {
                const val = ds.data[lastIdx];
                if (val == null) return;
                const prev = ds.data[lastIdx - 1];
                const formatted = val.toFixed(1) + '%';
                let deltaClass = 'd-nt', deltaText = mc.labels[lastIdx];
                if (prev != null) {
                    const diff = (val - prev).toFixed(1);
                    deltaClass = diff >= 0 ? 'd-up' : 'd-dn';
                    deltaText = (diff >= 0 ? '▲ ' : '▼ ') + Math.abs(diff) + ' pp';
                }
                stats.push({ lbl: ds.label, val: formatted, deltaClass, deltaText });
            });
        }

        if (stats.length === 0) {
            section.style.display = 'none';
            return;
        }

        // Limit to 4 cards
        stats = stats.slice(0, 4);
        grid.innerHTML = stats.map(s => `
            <div class="stat-card">
                <div class="stat-lbl">${s.lbl}</div>
                <div class="stat-val">${s.val}</div>
                <span class="stat-delta ${s.deltaClass}">${s.deltaText}</span>
            </div>`).join('');
        section.style.display = 'block';
    }

    function renderAllCharts() {

        const data = window.latestChartsData;
        if (!data) return;

        // Chart 1: Financials
        if (data.financial_chart) {
            initOrUpdateChart('chartFinancials', {
                type: 'bar',
                data: {
                    labels: data.financial_chart.labels,
                    datasets: data.financial_chart.datasets.map(d => ({
                        label: d.label,
                        data: d.data,
                        backgroundColor: d.color,
                        borderRadius: 6
                    }))
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#94a3b8' } } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
        }

        // Chart 2: Margins
        if (data.margins_chart) {
            initOrUpdateChart('chartMargins', {
                type: 'bar',
                data: {
                    labels: data.margins_chart.labels,
                    datasets: data.margins_chart.datasets.map(d => ({
                        type: d.type || 'bar',
                        label: d.label,
                        data: d.data,
                        borderColor: d.color,
                        backgroundColor: d.type === 'line' ? 'transparent' : d.color,
                        borderWidth: d.type === 'line' ? 3 : 1,
                        borderRadius: 6
                    }))
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#94a3b8' } } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
        }

        // Chart 3: Shareholding
        if (data.shareholding_chart) {
            initOrUpdateChart('chartShareholding', {
                type: 'line',
                data: {
                    labels: data.shareholding_chart.labels,
                    datasets: data.shareholding_chart.datasets.map(d => ({
                        label: d.label,
                        data: d.data,
                        borderColor: d.color,
                        backgroundColor: d.color + '22',
                        borderWidth: 2.5,
                        fill: false,
                        tension: 0.3
                    }))
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#94a3b8' } } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
        }

        // Chart 4: Operations
        if (data.operations_chart) {
            const ops = data.operations_chart;
            initOrUpdateChart('chartOperations', {
                type: 'bar',
                data: {
                    labels: ops.receivable_days.labels,
                    datasets: [
                        {
                            label: ops.receivable_days.label,
                            data: ops.receivable_days.data,
                            backgroundColor: ops.receivable_days.color,
                            borderRadius: 6
                        },
                        {
                            label: ops.order_book.label,
                            data: ops.order_book.data,
                            backgroundColor: ops.order_book.color,
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#94a3b8' } } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
        }
    }

    function initOrUpdateChart(canvasId, config) {
        if (chartsInstances[canvasId]) {
            chartsInstances[canvasId].destroy();
        }
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        chartsInstances[canvasId] = new Chart(ctx, config);
    }

    function triggerDirectUpload() {
        document.getElementById('directFileInput').click();
    }

    async function handleDirectFileSelect(event) {
        const files = Array.from(event.target.files);
        if (!files.length) return;

        const ticker = getActiveTicker();
        const total = files.length;
        let done = 0;
        let failed = [];

        // Show progress toast
        let toast = document.getElementById('uploadToast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'uploadToast';
            toast.style.cssText = 'position:fixed;bottom:24px;right:24px;background:#1e293b;color:#e2e8f0;padding:14px 20px;border-radius:12px;font-size:13px;z-index:9999;border:1px solid #334155;min-width:240px;box-shadow:0 8px 32px rgba(0,0,0,0.4);';
            document.body.appendChild(toast);
        }

        const updateToast = () => {
            toast.innerHTML = `<div style="font-weight:600;margin-bottom:6px;">📤 Uploading files…</div>
                <div style="color:#94a3b8;">${done} / ${total} uploaded${failed.length ? ` &nbsp;⚠️ ${failed.length} failed` : ''}</div>
                <div style="margin-top:8px;background:#334155;border-radius:6px;height:6px;">
                  <div style="background:#6366f1;height:6px;border-radius:6px;width:${Math.round((done/total)*100)}%;transition:width 0.3s;"></div>
                </div>`;
        };
        updateToast();

        async function uploadOneFile(file) {
            return new Promise((resolve) => {
                const reader = new FileReader();
                if (file.name.toLowerCase().endsWith('.pdf')) {
                    reader.onload = async function(e) {
                        await uploadPayload({
                            ticker: ticker,
                            filename: file.name,
                            source: file.name.replace(/\.[^/.]+$/, ""),
                            date: getActiveDate(),
                            doc_type: "PDF Document",
                            file_base64: e.target.result
                        });
                        resolve();
                    };
                    reader.readAsDataURL(file);
                } else {
                    reader.onload = async function(e) {
                        await uploadPayload({
                            ticker: ticker,
                            filename: file.name,
                            source: file.name.replace(/\.[^/.]+$/, ""),
                            date: getActiveDate(),
                            doc_type: "Document",
                            content: e.target.result
                        });
                        resolve();
                    };
                    reader.readAsText(file);
                }
            });
        }

        for (const file of files) {
            try {
                await uploadOneFile(file);
                done++;
            } catch (e) {
                failed.push(file.name);
                done++;
            }
            updateToast();
        }

        // Final state
        if (failed.length) {
            toast.innerHTML = `<div style="font-weight:600;margin-bottom:4px;">⚠️ Upload complete with errors</div>
                <div style="color:#94a3b8;">${total - failed.length}/${total} succeeded. Failed: ${failed.join(', ')}</div>`;
        } else {
            toast.innerHTML = `<div style="font-weight:600;color:#4ade80;">✅ All ${total} file${total>1?'s':''} uploaded!</div>`;
        }
        setTimeout(() => { toast.remove(); }, 3000);

        await loadDocumentsList();
        document.getElementById('directFileInput').value = "";
    }

    async function uploadPayload(payload) {
        try {
            const resp = await fetch('/api/upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const res = await resp.json();
            if (res.success) {
                await loadDocumentsList();
                // Clear file input
                document.getElementById('directFileInput').value = "";
            }
        } catch (e) {
            alert('Error uploading document: ' + e);
        }
    }

    // ── Custom Delete Modal ──────────────────────────
    let _pendingDeleteFile = null;

    function deleteDocument(filename) {
        _pendingDeleteFile = filename;
        document.getElementById('deleteModalFilename').innerText = filename;
        document.getElementById('deleteModal').classList.add('open');
    }

    function closeDeleteModal() {
        _pendingDeleteFile = null;
        document.getElementById('deleteModal').classList.remove('open');
    }

    // Close on backdrop click
    document.getElementById('deleteModal').addEventListener('click', function(e) {
        if (e.target === this) closeDeleteModal();
    });

    // Wire confirm button
    document.getElementById('deleteModalConfirm').addEventListener('click', async function() {
        const filename = _pendingDeleteFile;
        if (!filename) return;
        closeDeleteModal();
        const ticker = getActiveTicker();
        try {
            const resp = await fetch('/api/documents', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker: ticker, filename: filename })
            });
            const res = await resp.json();
            if (res.success) {
                // Show a brief success toast
                const t = document.createElement('div');
                t.style.cssText = 'position:fixed;bottom:24px;right:24px;background:#122033;color:#34d399;padding:12px 18px;border-radius:10px;font-size:13px;font-weight:600;z-index:9999;border:1px solid rgba(52,211,153,.3);box-shadow:0 8px 28px rgba(0,0,0,.4);';
                t.innerText = '✓ Deleted ' + filename;
                document.body.appendChild(t);
                setTimeout(() => t.remove(), 2500);
                loadDocumentsList();
            }
        } catch (e) {
            console.error('Error deleting document:', e);
        }
    });

    function copyBrief() {
        if (!rawBriefMarkdown) {
            alert('Please generate or wait for the brief to load first.');
            return;
        }
        navigator.clipboard.writeText(rawBriefMarkdown).then(() => {
            const btn = document.getElementById('btnCopyBrief');
            const orig = btn.innerHTML;
            btn.innerHTML = '✅ Copied!';
            setTimeout(() => { btn.innerHTML = orig; }, 2000);
        });
    }

    // Direct Drag and Drop on dropCard
    const dropCard = document.getElementById('dropCard');
    if (dropCard) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropCard.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropCard.classList.add('drag-over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropCard.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropCard.classList.remove('drag-over');
            }, false);
        });

        dropCard.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                handleDirectFileSelect({ target: { files: files } });
            }
        }, false);
    }

    async function init() {
        await loadDocumentsList();
        await runAgent();
    }

    window.onload = init;
</script>

</body>
</html>
"""

class AgentServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
            return

        elif parsed.path == "/api/documents":
            params = urllib.parse.parse_qs(parsed.query)
            ticker = params.get("ticker", ["SRVCABLE"])[0].upper()
            target_dir = os.path.join(PACKS_DIR, ticker)
            os.makedirs(target_dir, exist_ok=True)

            docs_list = []
            if os.path.exists(target_dir):
                valid_exts = (".md", ".txt", ".pdf", ".csv")
                files = sorted([f for f in os.listdir(target_dir) if f.lower().endswith(valid_exts) and f != "README.md"])
                for f in files:
                    filepath = os.path.join(target_dir, f)
                    try:
                        size_kb = round(os.path.getsize(filepath) / 1024, 1)
                        source = f.replace(".md", "").replace(".txt", "").replace(".pdf", "")
                        date = "2026-09-23"
                        doc_type = "PDF Document" if f.lower().endswith(".pdf") else "Document"

                        if not f.lower().endswith(".pdf"):
                            with open(filepath, "r", encoding="utf-8", errors="replace") as fp:
                                content = fp.read()
                            fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
                            if fm:
                                for line in fm.group(1).splitlines():
                                    if line.startswith("source:"):
                                        source = line.split(":", 1)[1].strip()
                                    elif line.startswith("published:"):
                                        date = line.split(":", 1)[1].strip()
                                    elif line.startswith("type:"):
                                        doc_type = line.split(":", 1)[1].strip()

                        tier = 2
                        low = (source + " " + doc_type).lower()
                        if any(k in low for k in ["official", "nse", "concall", "press release", "filing"]):
                            tier = 1
                        elif any(k in low for k in ["blog", "telegram", "multibagger"]):
                            tier = 3

                        docs_list.append({
                            "filename": f,
                            "source": source,
                            "date": date,
                            "doc_type": doc_type,
                            "size_kb": size_kb,
                            "tier": tier
                        })
                    except Exception as e:
                        pass

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(docs_list).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = json.loads(body) if body else {}

        if parsed.path == "/api/upload":
            ticker = data.get("ticker", "SRVCABLE").strip().upper()
            filename = data.get("filename", f"doc_{int(os.getpid())}.md").strip()
            source = data.get("source", "User Upload").strip()
            date = data.get("date", "2026-09-23").strip()
            doc_type = data.get("doc_type", "Research Note").strip()
            content = data.get("content", "").strip()
            file_base64 = data.get("file_base64", None)

            target_dir = os.path.join(PACKS_DIR, ticker)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)

            if file_base64:
                if "," in file_base64:
                    file_base64 = file_base64.split(",", 1)[1]
                file_bytes = base64.b64decode(file_base64)
                with open(filepath, "wb") as f:
                    f.write(file_bytes)
            else:
                formatted_file = f"""---
source: {source}
url: local://uploads/{ticker}/{filename}
published: {date}
type: {doc_type}
---

{content}
"""
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(formatted_file)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "filename": filename}).encode("utf-8"))
            return

        elif parsed.path == "/api/run":
            ticker = data.get("ticker", "SRVCABLE").strip().upper()
            ref_date = data.get("reference_date", "2026-09-23").strip()
            target_dir = os.path.join(PACKS_DIR, ticker)
            os.makedirs(target_dir, exist_ok=True)

            config = AgentConfig(
                ticker=ticker,
                docs_dir=target_dir,
                reference_date=ref_date
            )
            agent = ResearchAgent(config)
            result = agent.run()

            response_data = {
                "ticker": result["ticker"],
                "brief_markdown": result["brief_markdown"],
                "validation_passed": result["validation_passed"],
                "doc_count": result["doc_count"],
                "injections_blocked": result["injections_blocked"],
                "entity_mismatches_identified": result["entity_mismatches_identified"],
                "conflicts_resolved": result["conflicts_resolved"],
                "charts_data": result.get("charts_data", {})
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/documents":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body) if body else {}

            ticker = data.get("ticker", "SRVCABLE").strip().upper()
            filename = data.get("filename", "").strip()
            target_file = os.path.join(PACKS_DIR, ticker, filename)

            if os.path.exists(target_file):
                try:
                    os.remove(target_file)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
                    return
                except Exception as e:
                    pass

            self.send_response(400)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

def run_server():
    with socketserver.TCPServer(("", PORT), AgentServerHandler) as httpd:
        print(f"Autonomous Equity Research Agent running at http://127.0.0.1:{PORT}/")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
