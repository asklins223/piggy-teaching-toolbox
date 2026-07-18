/**
 * Characters API module
 * Requirements: 3.2
 */

import api from './index'

// Types
export interface CharacterInfo {
  character_id: string
  name: string
  description: string
  image_url: string
  user_id?: string
}

export interface CharacterLibraryResponse {
  characters: CharacterInfo[]
}

export interface GenerateCharacterRequest {
  name: string
  description: string
}

export interface GenerateCharacterResponse {
  character_id: string
  name: string
  image_url: string
}

export interface RandomTemplateResponse {
  name: string
  description: string
}

export interface GenerateCharacterIdeaResponse {
  name: string
  description: string
}

export interface AddCharacterToProjectRequest {
  character_id: string
}

export interface AddCharacterToProjectResponse {
  success: boolean
}

export interface ProjectCharactersResponse {
  characters: CharacterInfo[]
}

// API functions

/**
 * Get list of all characters in the library
 */
export async function getCharacterLibrary(): Promise<CharacterLibraryResponse> {
  const response = await api.get<CharacterLibraryResponse>('/characters/library')
  return response.data
}

/**
 * Generate a new character and add it to the library
 */
export async function generateCharacter(data: GenerateCharacterRequest): Promise<GenerateCharacterResponse> {
  const response = await api.post<GenerateCharacterResponse>('/characters/generate', data)
  return response.data
}

/**
 * Get a random character template
 */
export async function getRandomTemplate(): Promise<RandomTemplateResponse> {
  const response = await api.get<RandomTemplateResponse>('/characters/random-template')
  return response.data
}

/**
 * AI generate character idea (name and description)
 */
export async function generateCharacterIdea(): Promise<GenerateCharacterIdeaResponse> {
  const response = await api.post<GenerateCharacterIdeaResponse>('/characters/ai-generate-idea')
  return response.data
}

/**
 * Add a character from the library to a project
 */
export async function addCharacterToProject(
  projectId: string,
  characterId: string
): Promise<AddCharacterToProjectResponse> {
  const response = await api.post<AddCharacterToProjectResponse>(
    `/projects/${projectId}/characters`,
    { character_id: characterId }
  )
  return response.data
}

/**
 * Get list of characters in a project
 */
export async function getProjectCharacters(projectId: string): Promise<ProjectCharactersResponse> {
  const response = await api.get<ProjectCharactersResponse>(`/projects/${projectId}/characters`)
  return response.data
}

/**
 * Delete a character from the library
 */
export async function deleteCharacter(characterId: string): Promise<{ success: boolean }> {
  const response = await api.delete<{ success: boolean }>(`/characters/${characterId}`)
  return response.data
}

/**
 * Remove a character from a project
 */
export async function removeCharacterFromProject(
  projectId: string,
  characterId: string
): Promise<{ success: boolean }> {
  const response = await api.delete<{ success: boolean }>(
    `/projects/${projectId}/characters/${characterId}`
  )
  return response.data
}
