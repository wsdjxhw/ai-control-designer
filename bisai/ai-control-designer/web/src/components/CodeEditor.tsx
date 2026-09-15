import React from 'react';
import MonacoEditor from '@monaco-editor/react';

interface CodeEditorProps {
  value: string;
  onChange?: (value: string) => void;
  language?: 'python' | 'json' | 'javascript' | 'typescript';
  height?: string | number;
  readOnly?: boolean;
  label?: string;
  className?: string;
}

const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  language = 'python',
  height = 200,
  readOnly = false,
  label,
  className = '',
}) => {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <div
        className="border border-gray-300 rounded-lg overflow-hidden"
        style={{ height: typeof height === 'number' ? height : height }}
      >
        <MonacoEditor
          height="100%"
          defaultLanguage={language}
          value={value}
          onChange={(val) => onChange?.(val || '')}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            readOnly,
            automaticLayout: true,
            scrollBeyondLastLine: false,
          }}
        />
      </div>
    </div>
  );
};

export default CodeEditor;