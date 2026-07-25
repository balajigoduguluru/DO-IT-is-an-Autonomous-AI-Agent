import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css'; // Premium dark mode syntax highlighting

export function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="prose prose-invert prose-do-it max-w-none">
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]} 
        rehypePlugins={[rehypeHighlight]}
        components={{
          a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" className="text-do-active hover:underline" />,
          code: ({ node, inline, ...props }: any) => 
            inline ? (
              <code {...props} className="bg-do-bg-tertiary px-1.5 py-0.5 rounded-md text-[13px] font-mono text-do-text-primary" />
            ) : (
              <code {...props} />
            )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
