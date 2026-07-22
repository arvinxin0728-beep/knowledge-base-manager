#!/usr/bin/env ruby
# frozen_string_literal: true

require "digest"
require "optparse"
require "pathname"

options = { apply: false }
parser = OptionParser.new do |p|
  p.banner = "Usage: manage_library.rb COMMAND [options]"
  p.on("--base PATH", "Path to 笔记同步助手") { |v| options[:base] = v }
  p.on("--from DATE", "Inclusive start date") { |v| options[:from] = v }
  p.on("--to DATE", "Inclusive end date") { |v| options[:to] = v }
  p.on("--apply", "Perform the planned mutation") { options[:apply] = true }
  p.on("--quarantine PATH", "Move duplicate files here instead of deleting them") { |v| options[:quarantine] = v }
end

command = ARGV.shift
parser.parse!(ARGV)
abort parser.to_s unless %w[audit import-dates dedupe prune-empty].include?(command)

abort "--base PATH is required" unless options[:base]
base = Pathname(options[:base]).expand_path
target = base.join("公众号原始文章")
abort "Base directory not found: #{base}" unless base.directory?
abort "Target directory not found: #{target}" unless target.directory?

date_name = /^\d{4}-\d{2}-\d{2}$/
canonical_name = /^\d{4}-\d{2}-\d{2} .+\.md$/

def exact_groups(files)
  files.group_by { |f| Digest::SHA256.file(f).hexdigest }.values.select { |g| g.size > 1 }
end

def date_dirs(base, from, to, date_name)
  abort "--from and --to are required" unless from && to
  abort "Invalid date range" unless from.match?(date_name) && to.match?(date_name) && from <= to
  base.children.select do |p|
    p.directory? && p.basename.to_s.match?(date_name) && p.basename.to_s >= from && p.basename.to_s <= to
  end.sort
end

case command
when "audit"
  root_files = target.glob("*.md")
  nested = target.glob("**/*.md").reject { |p| p.dirname == target }
  bad = root_files.reject { |p| p.basename.to_s.match?(canonical_name) }
  duplicates = exact_groups(root_files)
  puts "root_articles=#{root_files.size}"
  puts "nested_articles=#{nested.size}"
  puts "bad_names=#{bad.size}"
  puts "duplicate_groups=#{duplicates.size}"
  puts "duplicate_extras=#{duplicates.sum { |g| g.size - 1 }}"
when "import-dates"
  dirs = date_dirs(base, options[:from], options[:to], date_name)
  files = dirs.flat_map { |d| d.glob("**/*.md") }
  non_md = dirs.flat_map { |d| d.glob("**/*", File::FNM_DOTMATCH) }.select do |p|
    p.file? && p.extname.downcase != ".md" && p.basename.to_s != ".DS_Store"
  end
  plan = files.map do |src|
    date = src.relative_path_from(base).each_filename.first
    title = src.basename(".md").to_s.sub(/^\d{4}-\d{2}-\d{2} /, "")
    [src, target.join("#{date} #{title}.md")]
  end
  internal = plan.group_by(&:last).select { |_dest, rows| rows.size > 1 }
  existing = plan.select { |_src, dest| dest.exist? }
  puts "date_dirs=#{dirs.size}"
  puts "articles=#{files.size}"
  puts "non_markdown=#{non_md.size}"
  puts "internal_conflicts=#{internal.size}"
  puts "existing_destinations=#{existing.size}"
  abort "Refusing to apply: resolve conflicts first" if options[:apply] && (!internal.empty? || !existing.empty?)
  if options[:apply]
    plan.each { |src, dest| src.rename(dest) }
    puts "moved=#{plan.size}"
  else
    puts "dry_run=true"
  end
when "dedupe"
  files = target.glob("*.md")
  groups = exact_groups(files)
  removals = groups.flat_map do |group|
    keeper = group.find { |p| !p.basename.to_s.end_with?(" 1.md") } || group.sort.first
    group - [keeper]
  end
  puts "duplicate_groups=#{groups.size}"
  puts "duplicate_extras=#{removals.size}"
  if options[:apply]
    abort "--quarantine PATH is required with dedupe --apply" unless options[:quarantine]
    quarantine = Pathname(options[:quarantine]).expand_path
    quarantine.mkpath
    conflicts = removals.select { |src| quarantine.join(src.basename).exist? }
    abort "Refusing to apply: quarantine filename conflicts=#{conflicts.size}" unless conflicts.empty?
    removals.each { |src| src.rename(quarantine.join(src.basename)) }
    puts "quarantined=#{removals.size}"
  else
    puts "dry_run=true"
  end
when "prune-empty"
  dirs = date_dirs(base, options[:from], options[:to], date_name)
  empty = dirs.select { |d| d.children.empty? }
  nonempty = dirs - empty
  puts "date_dirs=#{dirs.size}"
  puts "empty=#{empty.size}"
  puts "nonempty=#{nonempty.size}"
  if options[:apply]
    empty.each(&:rmdir)
    puts "removed=#{empty.size}"
  else
    puts "dry_run=true"
  end
end
