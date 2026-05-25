import { describe, test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { discoverSkills, loadSkill } from '../src/skills.js'

function makeTempDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'minicode-skills-test-'))
}

function writeSkill(root: string, name: string, content: string): string {
  const skillPath = path.join(root, '.tcm-agent', 'skills', name, 'SKILL.md')
  fs.mkdirSync(path.dirname(skillPath), { recursive: true })
  fs.writeFileSync(skillPath, content, 'utf8')
  return skillPath
}

describe('TCM skill discovery', () => {
  test('discovers project skills from .tcm-agent/skills', async () => {
    const dir = makeTempDir()
    try {
      const skillPath = writeSkill(dir, 'tcm-herb-query', '# Herb Query\n\nQuery herbs safely.')
      const skills = await discoverSkills(dir)

      assert.deepEqual(skills.map(skill => skill.name), ['tcm-herb-query'])
      assert.equal(skills[0].path, skillPath)
      assert.equal(skills[0].source, 'project')
      assert.equal(skills[0].description, 'Query herbs safely.')
    } finally {
      fs.rmSync(dir, { recursive: true, force: true })
    }
  })

  test('loads project skills from .tcm-agent/skills', async () => {
    const dir = makeTempDir()
    try {
      writeSkill(dir, 'tcm-safety', '# Safety\n\nCheck contraindications.')
      const skill = await loadSkill(dir, 'tcm-safety')

      assert.ok(skill)
      assert.equal(skill.name, 'tcm-safety')
      assert.equal(skill.source, 'project')
      assert.match(skill.content, /Check contraindications/)
    } finally {
      fs.rmSync(dir, { recursive: true, force: true })
    }
  })
})
