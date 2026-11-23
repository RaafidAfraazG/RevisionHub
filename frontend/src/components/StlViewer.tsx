import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { STLLoader } from 'three/addons/loaders/STLLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RotateCcw, Rotate3D } from 'lucide-react'
import { ErrorMessage, messageOf } from './ui'

export default function StlViewer({ attachmentId }: { attachmentId: number }) {
  const host = useRef<HTMLDivElement>(null)
  const fit = useRef<() => void>(() => {})
  const orbit = useRef<OrbitControls | null>(null)
  const [rotating, setRotating] = useState(false)
  const [metrics, setMetrics] = useState<{ dimensions: string; triangles: number } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    const container = host.current!
    const abort = new AbortController()
    let active = true, frame = 0
    let renderer: THREE.WebGLRenderer | undefined
    let geometry: THREE.BufferGeometry | undefined
    let material: THREE.MeshStandardMaterial | undefined
    let controls: OrbitControls | undefined
    let observer: ResizeObserver | undefined
    const resources: THREE.BufferGeometry[] = []
    const materials: THREE.Material[] = []
    setLoading(true); setError(''); setMetrics(null); setRotating(false)
    async function initialize() {
      try {
        const response = await fetch(`/api/attachments/${attachmentId}/download`, { signal: abort.signal })
        if (!response.ok) throw new Error('Unable to load this STL. Download the file to inspect it.')
        const buffer = await response.arrayBuffer()
        if (!active) return
        geometry = new STLLoader().parse(buffer)
        geometry.computeBoundingBox()
        const original = geometry.boundingBox!.getSize(new THREE.Vector3())
        setMetrics({ dimensions: [original.x, original.y, original.z].map(n => n.toFixed(1)).join(' × '), triangles: geometry.getAttribute('position').count / 3 })
        geometry.rotateX(-Math.PI / 2)
        geometry.center(); geometry.computeBoundingSphere()
        const radius = geometry.boundingSphere?.radius || 0
        if (!Number.isFinite(radius) || radius <= 0) throw new Error('This STL has no valid 3D geometry.')
        // Normalize arbitrary CAD units so clipping and lighting remain stable.
        geometry.scale(1 / radius, 1 / radius, 1 / radius)
        const scene = new THREE.Scene(); scene.background = new THREE.Color('#f0f1f3')
        const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 100)
        renderer = new THREE.WebGLRenderer({ antialias: true })
        renderer.outputColorSpace = THREE.SRGBColorSpace
        renderer.toneMapping = THREE.ACESFilmicToneMapping
        renderer.toneMappingExposure = 1.15
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
        renderer.domElement.setAttribute('aria-label', 'Interactive STL model. Drag to rotate; scroll or pinch to zoom.')
        renderer.domElement.setAttribute('role', 'img')
        container.appendChild(renderer.domElement)
        material = new THREE.MeshStandardMaterial({ color: '#8a9bb0', roughness: 0.32, metalness: 0.55 })
        scene.add(new THREE.Mesh(geometry, material))
        scene.add(new THREE.HemisphereLight('#ffffff', '#a1a6b0', 2.3))
        const light = new THREE.DirectionalLight('#ffffff', 3.5); light.position.set(3, 5, 4); scene.add(light)
        const fill = new THREE.DirectionalLight('#dfe8f4', 1.5); fill.position.set(-4, 2, -3); scene.add(fill)
        geometry.computeBoundingBox()
        const groundY = geometry.boundingBox!.min.y - .025
        const grid = new THREE.GridHelper(8, 40, '#c6cbd3', '#dce0e5'); grid.position.y = groundY
        scene.add(grid); resources.push(grid.geometry)
        materials.push(...(Array.isArray(grid.material) ? grid.material : [grid.material]))
        controls = new OrbitControls(camera, renderer.domElement)
        orbit.current = controls; controls.autoRotateSpeed = 2
        controls.enableDamping = true; controls.minDistance = 1.2; controls.maxDistance = 25
        fit.current = () => {
          const vertical = THREE.MathUtils.degToRad(camera.fov / 2)
          const horizontal = Math.atan(Math.tan(vertical) * camera.aspect)
          const distance = 1.2 / Math.sin(Math.min(vertical, horizontal))
          camera.position.copy(new THREE.Vector3(1, 1.25, 1).normalize().multiplyScalar(distance))
          controls?.target.set(0, 0, 0); controls?.update()
        }
        const resize = () => {
          const width = Math.max(container.clientWidth, 1), height = Math.max(container.clientHeight, 1)
          renderer!.setSize(width, height); camera.aspect = width / height; camera.updateProjectionMatrix()
          fit.current()
        }
        observer = new ResizeObserver(resize); observer.observe(container); resize()
        const animate = () => { if (!active) return; controls!.update(); renderer!.render(scene, camera); frame = requestAnimationFrame(animate) }
        animate(); setLoading(false)
      } catch (e) {
        if (active) { setError(messageOf(e)); setLoading(false) }
      }
    }
    void initialize()
    return () => {
      active = false; abort.abort(); cancelAnimationFrame(frame); observer?.disconnect()
      controls?.dispose(); orbit.current = null; geometry?.dispose(); material?.dispose()
      resources.forEach(r => r.dispose()); materials.forEach(m => m.dispose()); renderer?.dispose()
      renderer?.domElement.remove(); fit.current = () => {}
    }
  }, [attachmentId])
  return <div className="stl-viewer"><div ref={host} className="stl-canvas" />{metrics && !error && <div className="viewer-metrics"><div>{metrics.dimensions} model units (X × Y × Z)</div><div>{metrics.triangles.toLocaleString()} triangles</div></div>}{loading && <div className="viewer-overlay" role="status">Loading 3D model…</div>}{error && <div className="viewer-overlay"><ErrorMessage message={`${error} Your browser needs WebGL for STL preview.`} /></div>}<div className="viewer-toolbar"><span className="viewer-hint">Drag to orbit · Scroll to zoom · Generated models use mm</span><div className="viewer-tools"><button className="button secondary small" aria-pressed={rotating} disabled={loading || !!error} onClick={() => { const next = !rotating; setRotating(next); if (orbit.current) orbit.current.autoRotate = next }}><Rotate3D size={14} />Auto-rotate {rotating ? 'on' : 'off'}</button><button className="button secondary small" disabled={loading || !!error} onClick={() => { setRotating(false); if (orbit.current) orbit.current.autoRotate = false; fit.current() }}><RotateCcw size={14} />Reset view</button></div></div></div>
}
