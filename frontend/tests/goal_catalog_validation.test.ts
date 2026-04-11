import assert from 'node:assert/strict';
import test from 'node:test';
import catalogData from '../src/data/education-catalog.generated.json';
import { searchMajors } from '../src/lib/educationCatalog';
import { coerceMajorForUniversity, validateGoalSelection } from '../src/lib/goalValidation';

interface CatalogFile {
  universities: Array<{
    name: string;
    majors: string[];
  }>;
}

const catalog = catalogData as CatalogFile;

function findUniversityWithMajors() {
  const university = catalog.universities.find((item) => item.majors.length > 0);
  if (!university) {
    throw new Error('No university with majors was found in the catalog.');
  }
  return university;
}

function findMismatchedPair() {
  for (const source of catalog.universities) {
    const major = source.majors[0];
    if (!major) continue;

    const target = catalog.universities.find(
      (candidate) => candidate.name !== source.name && !candidate.majors.includes(major),
    );

    if (target) {
      return {
        sourceUniversity: source.name,
        targetUniversity: target.name,
        major,
      };
    }
  }

  throw new Error('No mismatched university-major pair was found in the catalog.');
}

test('searchMajors only returns majors that belong to the selected university', () => {
  const university = findUniversityWithMajors();
  const query = university.majors[0];
  const results = searchMajors(query, university.name, 20);

  assert.ok(results.length > 0);
  assert.ok(results.every((item) => validateGoalSelection(university.name, item.label).valid));
});

test('goal validation rejects a major that does not belong to the selected university', () => {
  const { targetUniversity, major } = findMismatchedPair();

  assert.equal(coerceMajorForUniversity(targetUniversity, major), '');
  assert.equal(validateGoalSelection(targetUniversity, major).valid, false);
});
