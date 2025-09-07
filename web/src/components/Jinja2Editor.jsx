import React, { useEffect, useMemo } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { vscodeDark, vscodeLight } from '@uiw/codemirror-theme-vscode';
import { python } from '@codemirror/lang-python';
import { html } from '@codemirror/lang-html';
import { StreamLanguage } from '@codemirror/language';
import { autocompletion, CompletionContext } from '@codemirror/autocomplete';
import { linter } from '@codemirror/lint';
import { search, searchKeymap } from '@codemirror/search';
import { keymap, EditorView } from '@codemirror/view';
import { defaultKeymap, indentWithTab } from '@codemirror/commands';

/**
 * Jinja2 Template Editor Component
 * 
 * A specialized code editor for Jinja2 templates with:
 * - Proper Jinja2 syntax highlighting
 * - Auto-completion for Jinja2 tags and variables
 * - Template validation
 * - Theme support (light/dark)
 */

// Custom Jinja2 language mode that combines HTML and Python
const jinja2Language = StreamLanguage.define({
  name: 'jinja2',
  startState: () => ({
    inJinja: false,
    jinjaType: null, // 'variable', 'block', 'comment'
  }),
  
  token: (stream, state) => {
    // Check for Jinja2 delimiters
    if (!state.inJinja) {
      // Variable tags {{ }}
      if (stream.match('{{')) {
        state.inJinja = true;
        state.jinjaType = 'variable';
        return 'keyword';
      }
      // Block tags {% %}
      if (stream.match('{%')) {
        state.inJinja = true;
        state.jinjaType = 'block';
        return 'keyword';
      }
      // Comment tags {# #}
      if (stream.match('{#')) {
        state.inJinja = true;
        state.jinjaType = 'comment';
        return 'comment';
      }
      
      // Regular HTML
      if (stream.match(/^[^{]+/)) {
        return 'text';
      }
      stream.next();
      return null;
    } else {
      // Inside Jinja2 tags
      if (state.jinjaType === 'variable' && stream.match('}}')) {
        state.inJinja = false;
        state.jinjaType = null;
        return 'keyword';
      }
      if (state.jinjaType === 'block' && stream.match('%}')) {
        state.inJinja = false;
        state.jinjaType = null;
        return 'keyword';
      }
      if (state.jinjaType === 'comment' && stream.match('#}')) {
        state.inJinja = false;
        state.jinjaType = null;
        return 'comment';
      }
      
      // Jinja2 keywords
      if (stream.match(/^(if|elif|else|endif|for|endfor|block|endblock|extends|include|macro|endmacro|set|with|endwith|trans|endtrans|pluralize|do|break|continue)\b/)) {
        return 'keyword.control';
      }
      
      // Jinja2 filters
      if (stream.match(/\|[\w_]+/)) {
        return 'function';
      }
      
      // Variables and properties
      if (stream.match(/[\w_]+(\.\w+)*/)) {
        return 'variable';
      }
      
      // Strings
      if (stream.match(/"[^"]*"|'[^']*'/)) {
        return 'string';
      }
      
      // Numbers
      if (stream.match(/\d+(\.\d+)?/)) {
        return 'number';
      }
      
      // Operators
      if (stream.match(/[+\-*/%=<>!&|]/)) {
        return 'operator';
      }
      
      stream.next();
      return state.jinjaType === 'comment' ? 'comment' : null;
    }
  },
  
  languageData: {
    commentTokens: {
      block: { open: '{#', close: '#}' },
    },
  },
});

// Jinja2 auto-completions
const jinja2Completions = (context) => {
  const word = context.matchBefore(/\w*/);
  if (!word || (word.from === word.to && !context.explicit)) return null;

  const completions = [
    // Block tags
    { label: '{% if %}', type: 'keyword', apply: '{% if ${}condition %}\n\t${}content\n{% endif %}' },
    { label: '{% for %}', type: 'keyword', apply: '{% for ${}item in ${}items %}\n\t${}content\n{% endfor %}' },
    { label: '{% block %}', type: 'keyword', apply: '{% block ${}name %}\n\t${}content\n{% endblock %}' },
    { label: '{% extends %}', type: 'keyword', apply: '{% extends "${}template.j2" %}' },
    { label: '{% include %}', type: 'keyword', apply: '{% include "${}template.j2" %}' },
    { label: '{% macro %}', type: 'keyword', apply: '{% macro ${}name(${}args) %}\n\t${}content\n{% endmacro %}' },
    { label: '{% set %}', type: 'keyword', apply: '{% set ${}variable = ${}value %}' },
    { label: '{% with %}', type: 'keyword', apply: '{% with ${}variable = ${}value %}\n\t${}content\n{% endwith %}' },
    
    // Variable tags
    { label: '{{ }}', type: 'variable', apply: '{{ ${}variable }}' },
    
    // Common filters
    { label: '|default', type: 'function', apply: '|default("${}default_value")' },
    { label: '|length', type: 'function', apply: '|length' },
    { label: '|lower', type: 'function', apply: '|lower' },
    { label: '|upper', type: 'function', apply: '|upper' },
    { label: '|capitalize', type: 'function', apply: '|capitalize' },
    { label: '|title', type: 'function', apply: '|title' },
    { label: '|trim', type: 'function', apply: '|trim' },
    { label: '|truncate', type: 'function', apply: '|truncate(${}50)' },
    { label: '|join', type: 'function', apply: '|join(", ")' },
    { label: '|replace', type: 'function', apply: '|replace("${}old", "${}new")' },
    { label: '|round', type: 'function', apply: '|round(${}2)' },
    { label: '|int', type: 'function', apply: '|int' },
    { label: '|float', type: 'function', apply: '|float' },
    { label: '|abs', type: 'function', apply: '|abs' },
    { label: '|format', type: 'function', apply: '|format(${}args)' },
    { label: '|escape', type: 'function', apply: '|escape' },
    { label: '|safe', type: 'function', apply: '|safe' },
    { label: '|tojson', type: 'function', apply: '|tojson' },
    { label: '|date', type: 'function', apply: '|date("%Y-%m-%d")' },
    
    // Common Jellynouncer variables
    { label: 'item.name', type: 'property', info: 'Media item name' },
    { label: 'item.year', type: 'property', info: 'Release year' },
    { label: 'item.overview', type: 'property', info: 'Item description' },
    { label: 'item.item_type', type: 'property', info: 'Type of media' },
    { label: 'item.series_name', type: 'property', info: 'TV series name' },
    { label: 'item.season_number', type: 'property', info: 'Season number' },
    { label: 'item.episode_number', type: 'property', info: 'Episode number' },
    { label: 'item.video_height', type: 'property', info: 'Video resolution height' },
    { label: 'item.video_codec', type: 'property', info: 'Video codec (H264, H265, etc)' },
    { label: 'item.audio_codec', type: 'property', info: 'Audio codec' },
    { label: 'item.audio_channels', type: 'property', info: 'Number of audio channels' },
    { label: 'item.video_range', type: 'property', info: 'HDR type' },
    { label: 'item.runtime_mins', type: 'property', info: 'Runtime in minutes' },
    { label: 'item.file_size_gb', type: 'property', info: 'File size in GB' },
    { label: 'item.imdb_id', type: 'property', info: 'IMDb identifier' },
    { label: 'item.tmdb_id', type: 'property', info: 'TMDb identifier' },
    { label: 'item.tvdb_id', type: 'property', info: 'TVDb identifier' },
    { label: 'item.critics_rating', type: 'property', info: 'Critics rating' },
    { label: 'item.community_rating', type: 'property', info: 'Community rating' },
    { label: 'item.genres', type: 'property', info: 'List of genres' },
    { label: 'item.studios', type: 'property', info: 'Production studios' },
    { label: 'item.tags', type: 'property', info: 'Tags list' },
    { label: 'timestamp', type: 'variable', info: 'Current timestamp' },
    { label: 'event_type', type: 'variable', info: 'Type of event (new, upgraded)' },
  ];

  return {
    from: word.from,
    options: completions,
  };
};

// Basic Jinja2 linting
const jinja2Linter = () => (view) => {
  const diagnostics = [];
  const text = view.state.doc.toString();
  
  // Check for unclosed tags
  const openTags = (text.match(/{%|{{|{#/g) || []).length;
  const closeTags = (text.match(/%}|}}|#}/g) || []).length;
  
  if (openTags !== closeTags) {
    diagnostics.push({
      from: 0,
      to: text.length,
      severity: 'error',
      message: `Unclosed Jinja2 tags detected (${openTags} open, ${closeTags} closed)`,
    });
  }
  
  // Check for missing endif/endfor/endblock with proper whitespace control handling
  // Match all variations: {% if, {%- if, {%+ if, etc.
  const ifCount = (text.match(/{%-?\+?\s*if\s+/g) || []).length;
  const elifCount = (text.match(/{%-?\+?\s*elif\s+/g) || []).length;
  const endifCount = (text.match(/{%-?\+?\s*endif\s*-?\+?%}/g) || []).length;
  
  // For if/elif/endif, we need: one endif for each if (elif doesn't need its own endif)
  const expectedEndifs = ifCount;
  if (expectedEndifs !== endifCount) {
    diagnostics.push({
      from: 0,
      to: text.length,
      severity: 'error',
      message: `Missing {% endif %} tags (${ifCount} if, ${elifCount} elif, ${endifCount} endif)`,
    });
  }
  
  const forCount = (text.match(/{%-?\+?\s*for\s+/g) || []).length;
  const endforCount = (text.match(/{%-?\+?\s*endfor\s*-?\+?%}/g) || []).length;
  if (forCount !== endforCount) {
    diagnostics.push({
      from: 0,
      to: text.length,
      severity: 'error',
      message: `Missing {% endfor %} tags (${forCount} for, ${endforCount} endfor)`,
    });
  }
  
  return diagnostics;
};

const Jinja2Editor = ({ 
  value, 
  onChange, 
  onSave,
  theme = 'dark',
  height = '600px',
  readOnly = false,
  placeholder = 'Enter your Jinja2 template here...',
  lineWrapping = false  // New prop to control line wrapping
}) => {
  // Extensions for the editor
  const extensions = useMemo(() => [
    jinja2Language,
    autocompletion({ override: [jinja2Completions] }),
    linter(jinja2Linter()),
    search(),
    // Configure editor view with proper wrapping and scrolling
    EditorView.theme({
      '&': {
        maxWidth: '100%',
      },
      '.cm-scroller': {
        fontFamily: 'ui-monospace, monospace',
        fontSize: '14px',
        overflowX: lineWrapping ? 'hidden' : 'auto',
      },
      '.cm-content': {
        minHeight: '200px',
        padding: '10px',
      },
      '.cm-editor': {
        height: height,
      },
      '.cm-editor.cm-focused': {
        outline: 'none',
      },
      // Fix for long lines
      '.cm-line': {
        wordBreak: lineWrapping ? 'break-word' : 'normal',
        whiteSpace: lineWrapping ? 'pre-wrap' : 'pre',
      }
    }),
    // Line wrapping extension
    lineWrapping ? EditorView.lineWrapping : [],
    keymap.of([
      ...defaultKeymap,
      ...searchKeymap,
      indentWithTab,
      // Custom save shortcut
      {
        key: 'Ctrl-s',
        mac: 'Cmd-s',
        preventDefault: true,
        run: () => {
          if (onSave) {
            onSave();
            return true;
          }
          return false;
        },
      },
    ]),
  ], [onSave, lineWrapping, height]);

  return (
    <div className="jinja2-editor-wrapper" style={{
      width: '100%',
      overflow: 'hidden',
      position: 'relative'
    }}>
      <CodeMirror
        value={value}
        height={height}
        theme={theme === 'dark' ? vscodeDark : vscodeLight}
        extensions={extensions}
        onChange={(val) => onChange && onChange(val)}
        editable={!readOnly}
        placeholder={placeholder}
        basicSetup={{
          lineNumbers: true,
          foldGutter: true,
          dropCursor: true,
          allowMultipleSelections: true,
          indentOnInput: true,
          bracketMatching: true,
          closeBrackets: true,
          autocompletion: true,
          rectangularSelection: true,
          highlightSelectionMatches: true,
          searchKeymap: true,
        }}
      />
    </div>
  );
};

export default Jinja2Editor;