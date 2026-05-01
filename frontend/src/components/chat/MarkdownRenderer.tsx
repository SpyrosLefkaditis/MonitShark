import "highlight.js/styles/github-dark.css";

import { type ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

type CodeProps = ComponentProps<"code"> & { inline?: boolean };

export function MarkdownRenderer({ source }: { source: string }) {
  return (
    <div className="markdown-body text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          p: ({ className, ...props }) => (
            <p className={cn("my-2 first:mt-0 last:mb-0", className)} {...props} />
          ),
          ul: ({ className, ...props }) => (
            <ul className={cn("list-disc pl-5 my-2 space-y-1", className)} {...props} />
          ),
          ol: ({ className, ...props }) => (
            <ol className={cn("list-decimal pl-5 my-2 space-y-1", className)} {...props} />
          ),
          h1: ({ className, ...props }) => (
            <h1 className={cn("text-base font-semibold mt-3 mb-2", className)} {...props} />
          ),
          h2: ({ className, ...props }) => (
            <h2 className={cn("text-sm font-semibold mt-3 mb-1.5", className)} {...props} />
          ),
          h3: ({ className, ...props }) => (
            <h3 className={cn("text-sm font-semibold mt-2 mb-1", className)} {...props} />
          ),
          a: ({ className, ...props }) => (
            <a
              className={cn("text-primary underline underline-offset-2", className)}
              target="_blank"
              rel="noreferrer noopener"
              {...props}
            />
          ),
          pre: ({ className, ...props }) => (
            <pre
              className={cn(
                "my-2 overflow-x-auto rounded-md border border-border bg-muted/40 p-3 text-xs font-mono",
                className,
              )}
              {...props}
            />
          ),
          code: ({ inline, className, children, ...props }: CodeProps) =>
            inline ? (
              <code
                className={cn(
                  "rounded bg-muted px-1 py-0.5 text-[0.85em] font-mono",
                  className,
                )}
                {...props}
              >
                {children}
              </code>
            ) : (
              <code className={cn("font-mono", className)} {...props}>
                {children}
              </code>
            ),
          table: ({ className, ...props }) => (
            <div className="my-2 overflow-x-auto">
              <table
                className={cn("text-xs border-collapse w-full", className)}
                {...props}
              />
            </div>
          ),
          th: ({ className, ...props }) => (
            <th
              className={cn(
                "border border-border bg-muted/50 px-2 py-1 text-left font-medium",
                className,
              )}
              {...props}
            />
          ),
          td: ({ className, ...props }) => (
            <td className={cn("border border-border px-2 py-1", className)} {...props} />
          ),
          blockquote: ({ className, ...props }) => (
            <blockquote
              className={cn(
                "my-2 border-l-2 border-border pl-3 italic text-muted-foreground",
                className,
              )}
              {...props}
            />
          ),
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
