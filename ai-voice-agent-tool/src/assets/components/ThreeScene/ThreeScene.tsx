import React, { useEffect, useRef } from "react";
import * as THREE from "three";

const ThreeScene: React.FC = () => {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const cleanupRef = useRef<() => void>(() => {});

  useEffect(() => {
    if (!hostRef.current) return;

    const width = hostRef.current.clientWidth || window.innerWidth;
    const height = hostRef.current.clientHeight || 400;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    hostRef.current.appendChild(renderer.domElement);

    const geometry = new THREE.SphereGeometry(1, 32, 32);
    const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
    const sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);

    camera.position.z = 5;

    let stop = false;
    const animate = () => {
      if (stop) return;
      requestAnimationFrame(animate);
      sphere.rotation.x += 0.01;
      sphere.rotation.y += 0.01;
      renderer.render(scene, camera);
    };
    animate();

    const onResize = () => {
      const w = hostRef.current?.clientWidth || window.innerWidth;
      const h = hostRef.current?.clientHeight || 400;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", onResize);

    cleanupRef.current = () => {
      stop = true;
      window.removeEventListener("resize", onResize);
      try {
        hostRef.current?.removeChild(renderer.domElement);
        renderer.dispose();
        geometry.dispose();
        material.dispose();
      } catch {}
    };

    return () => cleanupRef.current();
  }, []);

  return <div ref={hostRef} className="w-full h-[400px]" />;
};

export default ThreeScene;
