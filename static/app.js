// ===== UTILITY FUNCTIONS =====
const el = id => document.getElementById(id);
const showStatus = (msg, type = 'info') => {
  const status = el('status');
  status.textContent = msg;
  status.className = 'status-message ' + type;
};

const escapeHtml = s => {
  if (s === null || s === undefined) return '';
  const str = String(s);
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
};

// ===== SANITIZE & MARKDOWN HELPERS =====
function sanitizeMaterialText(raw) {
  if (!raw && raw !== 0) return '';
  let s = String(raw);

  // Aggressively extract content from wrapper structures
  // Try multiple patterns to find clean text trapped inside wrappers
  
  // Pattern 1: Extract from "text": "..." fields (most common)
  try {
    const matches = s.match(/\"text\"\s*:\s*\"((?:\\\\.|[^\"\\\\])*)\"/gs);
    if (matches && matches.length > 0) {
      // Join all extracted text segments
      const extracted = matches.map(m => {
        const val = m.match(/\"text\"\s*:\s*\"((?:\\\\.|[^\"\\\\])*)\"/);
        return val ? val[1] : '';
      }).filter(x => x.length > 0).join('\n\n');
      if (extracted.length > 10) {
        s = extracted;
      }
    }
  } catch (e) {}

  // Pattern 2: If still wrapped, try to find content after "text": marker
  if (s.includes('"text"')) {
    const parts = s.split('"text"');
    for (let i = parts.length - 1; i > 0; i--) {
      const part = parts[i];
      // Find content between quotes
      const m = part.match(/:\s*"((?:\\\\.|[^"\\\\])*)/);
      if (m && m[1] && m[1].length > 10) {
        s = m[1];
        break;
      }
    }
  }

  // Pattern 3: Strip obvious wrapper prefixes
  if (s.includes('response:\nGenerateContentResponse')) {
    s = s.split('response:\nGenerateContentResponse').pop() || s;
  }
  if (s.includes('response:')) {
    // Only take after if the rest looks reasonable
    const after = s.split('response:').pop();
    if (after && after.length > 10 && !after.includes('(')) {
      s = after;
    }
  }

  // Replace escaped newlines and carriage returns
  s = s.replace(/\\n/g, '\n').replace(/\\r/g, '\r').replace(/\\\//g, '/');

  // Unescape unicode escapes like \u2013
  s = s.replace(/\\u([0-9a-fA-F]{4})/g, function(_, code) {
    try { return String.fromCharCode(parseInt(code, 16)); } catch (e) { return '' }
  });

  // Replace escaped quotes
  s = s.replace(/\\\"/g, '"');

  // Remove any remaining wrapper markers or junk at the end
  s = s.replace(/\s*result=protos\.GenerateContentResponse\([\s\S]*$/i, '');
  s = s.replace(/[\n\s]*```[\s\S]*$/i, ''); // Remove code block markers at end if orphaned

  // Clean up common junk patterns
  s = s.replace(/^[\s\-:]*response[:\s]*/i, ''); // leading "response:" etc
  s = s.replace(/^[{[\s]*(done|iterator|result|candidates|content|parts)[:\s]*/i, ''); // JSON wrapper keys
  s = s.replace(/[\s\\]+$/g, ''); // trailing junk

  s = s.replace(/^\s*[:\-\s]+/, '');

  return s.trim();
}

function markdownToHtml(md) {
  if (!md) return '';
  // Escape HTML first
  let s = escapeHtml(md);

  // Code blocks ```
  s = s.replace(/```([\s\S]*?)```/g, function(_, code) {
    return '<pre class="code-block"><code>' + code.replace(/</g, '&lt;') + '</code></pre>';
  });

  // Headings
  s = s.replace(/^###\s*(.*)$/gm, '<h4>$1</h4>');
  s = s.replace(/^##\s*(.*)$/gm, '<h3>$1</h3>');
  s = s.replace(/^#\s*(.*)$/gm, '<h2>$1</h2>');

  // Bold **text**
  s = s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Inline code `code`
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Convert lines that start with '* ' into list items
  const listItems = [];
  s = s.replace(/^\*\s+(.*)$/gm, function(_, item) {
    listItems.push(item);
    return '<li>' + item + '</li>';
  });
  if (listItems.length) {
    s = s.replace(/(?:<li>[\s\S]*?<\/li>)+/, function(match) {
      return '<ul>' + match + '</ul>';
    });
  }

  // Paragraphs: replace double newlines with paragraph separators
  s = s.replace(/\n{2,}/g, '</p><p>');
  // Wrap with paragraph if not already block-level
  if (!s.startsWith('<h') && !s.startsWith('<pre') && !s.startsWith('<ul') && !s.startsWith('<p')) {
    s = '<p>' + s + '</p>';
  }

  return s;
}

// ===== CHARACTER COUNTER =====
el('transcript').addEventListener('input', (e) => {
  const count = e.target.value.length;
  el('char-count').textContent = count;
  const charCounter = e.target.parentElement.querySelector('.char-counter');
  if (count > 8000) {
    charCounter.style.color = '#EF4444';
  } else if (count > 5000) {
    charCounter.style.color = '#F59E0B';
  } else {
    charCounter.style.color = 'var(--text-secondary)';
  }
});

// ===== YOUTUBE PREVIEW =====
el('youtube').addEventListener('input', (e) => {
  const url = e.target.value.trim();
  const previewEl = el('youtube-preview');
  
  if (url.includes('youtube.com') || url.includes('youtu.be')) {
    previewEl.hidden = false;
    // Extract video ID for thumbnail
    const videoId = extractVideoId(url);
    if (videoId) {
      el('youtube-preview').querySelector('.preview-thumbnail').innerHTML = `
        <img src="https://img.youtube.com/vi/${videoId}/hqdefault.jpg" 
             style="width:100%; height:100%; object-fit:cover; border-radius:8px;" 
             onerror="this.style.display='none'">
      `;
      el('youtube-preview').querySelector('.preview-title').textContent = 'Video detected';
      showStatus('YouTube link recognized', 'success');
    }
  } else if (url.length > 0) {
    previewEl.hidden = true;
    showStatus('Enter a valid YouTube URL', 'info');
  } else {
    previewEl.hidden = true;
  }
});

function extractVideoId(url) {
  const regex = /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/;
  const match = url.match(regex);
  return match ? match[1] : null;
}

// ===== FORM INTERACTIONS =====
document.querySelectorAll('.input-field').forEach(input => {
  // Fade-in animation on focus
  input.addEventListener('focus', (e) => {
    e.target.parentElement.querySelector('.tooltip-hint')?.classList.add('show');
  });
  
  input.addEventListener('blur', (e) => {
    e.target.parentElement.querySelector('.tooltip-hint')?.classList.remove('show');
  });
});

// ===== MAIN GENERATE BUTTON =====
el('generate').addEventListener('click', async () => {
  const topic = el('topic').value.trim();
  const youtube = el('youtube').value.trim();
  const transcript = el('transcript').value.trim();
  const export_pdf = el('export_pdf').checked;
  const use_agent = el('use_agent').checked;

  // Validation
  if (!topic) {
    showStatus('Please enter a topic', 'error');
    return;
  }

  // Allow topic-only generation: user can provide only a topic and Gemini will synthesize content.
  if (!youtube && !transcript) {
    // proceed but notify user we're generating from topic only
    showStatus('Generating from topic (no transcript provided)...', 'info');
  }

  // Show progress
  showStatus('');
  el('progress').hidden = false;
  el('generate').disabled = true;

  try {
    const resp = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic,
        youtube_url: youtube || null,
        transcript_text: transcript || null,
        export_pdf,
        use_agent
      })
    });

    if (!resp.ok) {
      showStatus(`Server error: ${resp.status} ${resp.statusText}`, 'error');
      return;
    }

    let data;
    try {
      data = await resp.json();
    } catch (parseErr) {
      showStatus(`Failed to parse response: ${parseErr.message}`, 'error');
      console.error('Parse error:', parseErr);
      return;
    }

    if (data.error) {
      showStatus(`Error: ${data.error}`, 'error');
      return;
    }

    // Render results
    try {
      renderResults(data);
      // populate raw debug for troubleshooting
      try {
        const raw = el('raw-response');
        if (raw) {
          raw.textContent = JSON.stringify(data, null, 2);
          // show debug panel when summary is missing or arrays empty
          const shouldShow = !data.materials || !data.materials.summary || (Array.isArray(data.materials.flashcards) && data.materials.flashcards.length === 0 && Array.isArray(data.materials.quiz) && data.materials.quiz.length === 0);
          el('raw-debug').style.display = shouldShow ? 'block' : 'none';
        }
      } catch (e) {
        console.error('debug panel error', e);
      }

      showStatus('Study materials generated successfully!', 'success');
      
      // Smooth scroll to results
      setTimeout(() => {
        el('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 300);
    } catch (renderErr) {
      showStatus(`Render error: ${renderErr.message}`, 'error');
      console.error('Render error:', renderErr, data);
    }
  } catch (e) {
    showStatus(`Request failed: ${e.message}`, 'error');
    console.error(e);
  } finally {
    el('progress').hidden = true;
    el('generate').disabled = false;
  }
});

// ===== CLOSE RESULTS BUTTON =====
if (el('close-results')) {
  el('close-results').addEventListener('click', () => {
    el('results').hidden = true;
    el('topic').focus();
  });
}

// ===== RENDER RESULTS =====
function renderResults(data) {
  try {
    el('results').hidden = false;

    // Summary (sanitized + markdown -> HTML)
    const rawSummary = sanitizeMaterialText(data.materials?.summary || '');
    el('summary').innerHTML = rawSummary ? markdownToHtml(rawSummary) : '<p style="color:var(--text-secondary)">No summary available</p>';

    // Flashcards
    const fcArr = Array.isArray(data.materials?.flashcards) ? data.materials.flashcards : [];
    const fcContainer = el('flashcards');
    fcContainer.innerHTML = '';
    el('flashcard-count').textContent = `(${fcArr.length})`;

    fcArr.slice(0, 20).forEach(card => {
      try {
        const q = sanitizeMaterialText(card?.q || card?.question || '');
        const a = sanitizeMaterialText(card?.a || card?.answer || '');
        const li = document.createElement('li');
        // Render question and answer both as HTML for full readability
        const qHtml = q ? markdownToHtml(q) : '<em style="color:var(--text-secondary)">No question</em>';
        const aHtml = a ? markdownToHtml(a) : '<em style="color:var(--text-secondary)">No answer</em>';
        li.innerHTML = `<div class="flashcard-qa"><strong style="color:var(--accent-rose);">Q:</strong> ${qHtml}</div><div class="flashcard-qa"><strong style="color:var(--accent-emerald);">A:</strong> ${aHtml}</div>`;
        li.style.display = 'block';
        li.style.marginBottom = '16px';
        fcContainer.appendChild(li);
      } catch (e) {
        console.error('Flashcard render error:', e, card);
      }
    });

    // Quiz
    const quizArr = Array.isArray(data.materials?.quiz) ? data.materials.quiz : [];
    const quizContainer = el('quiz');
    quizContainer.innerHTML = '';
    el('quiz-count').textContent = `(${quizArr.length})`;

    quizArr.slice(0, 10).forEach((item, idx) => {
      try {
        const question = sanitizeMaterialText(item?.question || item?.q || '');
        const optionsArr = Array.isArray(item?.options) ? item.options : [];
        const answerIdx = typeof item?.answer === 'number' ? item.answer : null;
        const explanation = sanitizeMaterialText(item?.explanation || '');

        const li = document.createElement('li');
        const optionsHtml = optionsArr.map((opt, i) => {
          const isCorrect = i === answerIdx;
          const optText = sanitizeMaterialText(opt || '');
          const optRendered = markdownToHtml(optText);
          return `<div class="option${isCorrect ? ' correct' : ''}" style="padding:8px; margin:6px 0; border-radius:6px; ${isCorrect ? 'background:var(--accent-emerald-light, rgba(16,185,129,0.1)); border-left:3px solid var(--accent-emerald);' : 'background:var(--card-bg);'}">${isCorrect ? '✓ ' : ''}${optRendered}</div>`;
        }).join('');

        const questionHtml = markdownToHtml(question);
        const explanationHtml = markdownToHtml(explanation);
        
        li.innerHTML = `
          <div style="margin-bottom:12px;">${questionHtml}</div>
          <div class="options" style="margin:12px 0;">${optionsHtml || '<div class="option">No options available</div>'}</div>
          <div style="font-size:13px; color:var(--accent-emerald); margin-top:12px; padding:8px; background:var(--input-bg); border-radius:6px;"><strong>✓ Explanation:</strong> ${explanationHtml}</div>
        `;
        quizContainer.appendChild(li);
      } catch (e) {
        console.error('Quiz item render error:', e, item);
      }
    });

    // Study Plan
    const studyPlan = data.materials?.study_plan || {};
    const levels = Array.isArray(studyPlan.levels) ? studyPlan.levels : [];
    const planContainer = el('study_plan');
    planContainer.innerHTML = '';

    if (levels.length > 0) {
      levels.forEach(level => {
        try {
          const lvlName = String(level?.level || 'Unknown');
          const duration = String(level?.duration_days || 'N/A');
          const focus = String(level?.focus || 'No focus area');

          const card = document.createElement('div');
          card.className = 'study-level-card';
          card.innerHTML = `
            <div class="level-header">${escapeHtml(lvlName)}</div>
            <div class="level-detail"><span class="label">Duration:</span> ${escapeHtml(duration)} days</div>
            <div class="level-detail"><span class="label">Focus:</span> ${escapeHtml(focus)}</div>
          `;
          planContainer.appendChild(card);
        } catch (e) {
          console.error('Study plan card render error:', e, level);
        }
      });
    } else {
      planContainer.innerHTML = '<p style="color: var(--text-secondary); grid-column: 1/-1;">No study plan available</p>';
    }

    // PDF Download
    const pdfLink = el('pdf_link');
    pdfLink.innerHTML = '';
    if (data.pdf_filename) {
      const downloadBtn = document.createElement('a');
      downloadBtn.href = `/download?file=${encodeURIComponent(data.pdf_filename)}`;
      downloadBtn.className = 'download-btn';
      downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download PDF Study Pack';
      pdfLink.appendChild(downloadBtn);
    }
  } catch (e) {
    console.error('renderResults error:', e, data);
    showStatus(`Render error: ${e.message}`, 'error');
  }
}
