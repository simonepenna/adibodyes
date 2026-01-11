import { useState } from 'react';
import { useRef, useLayoutEffect } from 'react';
import { signIn, signOut, getCurrentUser } from 'aws-amplify/auth';
import { gsap } from 'gsap';
import { MorphSVGPlugin } from 'gsap/MorphSVGPlugin';
import '../aws-config';
import './Login.css';

gsap.registerPlugin(MorphSVGPlugin);

const Login = () => {
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const usernameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  
  // SVG element refs
  const armLRef = useRef<SVGGElement>(null);
  const armRRef = useRef<SVGGElement>(null);
  const eyeLRef = useRef<SVGGElement>(null);
  const eyeRRef = useRef<SVGGElement>(null);
  const noseRef = useRef<SVGPathElement>(null);
  const mouthRef = useRef<SVGGElement>(null);
  const mouthBGRef = useRef<SVGPathElement>(null);
  const mouthSmallBGRef = useRef<SVGPathElement>(null);
  const mouthMediumBGRef = useRef<SVGPathElement>(null);
  const mouthLargeBGRef = useRef<SVGPathElement>(null);
  const mouthOutlineRef = useRef<SVGPathElement>(null);
  const toothRef = useRef<SVGPathElement>(null);
  const tongueRef = useRef<SVGGElement>(null);
  const chinRef = useRef<SVGPathElement>(null);
  const faceRef = useRef<SVGPathElement>(null);
  const eyebrowRef = useRef<SVGGElement>(null);
  const outerEarLRef = useRef<SVGGElement>(null);
  const outerEarRRef = useRef<SVGGElement>(null);
  const earHairLRef = useRef<SVGGElement>(null);
  const earHairRRef = useRef<SVGGElement>(null);
  const hairRef = useRef<SVGPathElement>(null);

  let mouthStatus = "small";
  // const eyeMaxHorizD = 20;
  // const eyeMaxVertD = 10;
  const noseMaxHorizD = 23;
  const noseMaxVertD = 10;

  useLayoutEffect(() => {
    if (armLRef.current && armRRef.current) {
      gsap.set(armLRef.current, { x: -93, y: 220, rotation: 105, transformOrigin: "top left" });
      gsap.set(armRRef.current, { x: -93, y: 220, rotation: -105, transformOrigin: "top right" });
    }
  }, []);

  const getPosition = (el: HTMLElement | SVGElement | null): { x: number; y: number } => {
    if (!el) return { x: 0, y: 0 };
    
    let xPos = 0;
    let yPos = 0;
    let element: HTMLElement | null = el as HTMLElement;

    while (element) {
      if (element.tagName === "BODY") {
        const xScroll = element.scrollLeft || document.documentElement.scrollLeft;
        const yScroll = element.scrollTop || document.documentElement.scrollTop;
        xPos += element.offsetLeft - xScroll + element.clientLeft;
        yPos += element.offsetTop - yScroll + element.clientTop;
      } else {
        xPos += element.offsetLeft - element.scrollLeft + element.clientLeft;
        yPos += element.offsetTop - element.scrollTop + element.clientTop;
      }
      element = element.offsetParent as HTMLElement;
    }
    return { x: xPos, y: yPos };
  };

  const getAngle = (x1: number, y1: number, x2: number, y2: number) => {
    return Math.atan2(y1 - y2, x1 - x2);
  };

  const getCoord = () => {
    if (!usernameRef.current || !svgRef.current) return;

    const carPos = usernameRef.current.selectionEnd || 0;
    const div = document.createElement('div');
    const span = document.createElement('span');
    const copyStyle = getComputedStyle(usernameRef.current);

    Array.from(copyStyle).forEach((prop: string) => {
      (div.style as any)[prop] = (copyStyle as any)[prop];
    });
    
    div.style.position = 'absolute';
    document.body.appendChild(div);
    div.textContent = usernameRef.current.value.substr(0, carPos);
    span.textContent = usernameRef.current.value.substr(carPos) || '.';
    div.appendChild(span);

    const usernameCoords = getPosition(usernameRef.current);
    const caretCoords = getPosition(span);
    const centerCoords = getPosition(svgRef.current);
    const svgCoords = getPosition(svgRef.current);
    const svgRect = svgRef.current.getBoundingClientRect();
    const screenCenter = centerCoords.x + (svgRect.width / 2);
    const caretPos = caretCoords.x + usernameCoords.x;
    const dFromC = screenCenter - caretPos;

    // const eyeLCoords = { x: svgCoords.x + 84, y: svgCoords.y + 76 };
    // const eyeRCoords = { x: svgCoords.x + 113, y: svgCoords.y + 76 };
    const noseCoords = { x: svgCoords.x + 97, y: svgCoords.y + 81 };
    const mouthCoords = { x: svgCoords.x + 100, y: svgCoords.y + 100 };
    
    // const eyeLAngle = getAngle(eyeLCoords.x, eyeLCoords.y, usernameCoords.x + caretCoords.x, usernameCoords.y + 25);
    // const eyeLX = Math.cos(eyeLAngle) * eyeMaxHorizD;
    // const eyeLY = Math.sin(eyeLAngle) * eyeMaxVertD;
    
    // const eyeRAngle = getAngle(eyeRCoords.x, eyeRCoords.y, usernameCoords.x + caretCoords.x, usernameCoords.y + 25);
    // const eyeRX = Math.cos(eyeRAngle) * eyeMaxHorizD;
    // const eyeRY = Math.sin(eyeRAngle) * eyeMaxVertD;
    
    const noseAngle = getAngle(noseCoords.x, noseCoords.y, usernameCoords.x + caretCoords.x, usernameCoords.y + 25);
    const noseX = Math.cos(noseAngle) * noseMaxHorizD;
    const noseY = Math.sin(noseAngle) * noseMaxVertD;
    
    const mouthAngle = getAngle(mouthCoords.x, mouthCoords.y, usernameCoords.x + caretCoords.x, usernameCoords.y + 25);
    const mouthX = Math.cos(mouthAngle) * noseMaxHorizD;
    const mouthY = Math.sin(mouthAngle) * noseMaxVertD;
    const mouthR = Math.cos(mouthAngle) * 6;
    // const chinX = mouthX * 0.8;
    // const chinY = mouthY * 0.5;
    let chinS = 1 - ((dFromC * 0.15) / 100);
    if (chinS > 1) chinS = 1 - (chinS - 1);
    if (chinS < 0.5) chinS = 0.5; // Previene che la barba sparisca
    
    const faceX = mouthX * 0.3;
    const faceY = mouthY * 0.4;
    const faceSkew = Math.cos(mouthAngle) * 5;
    const eyebrowSkew = Math.cos(mouthAngle) * 25;
    const outerEarX = Math.cos(mouthAngle) * 4;
    const outerEarY = Math.cos(mouthAngle) * 5;
    const hairX = Math.cos(mouthAngle) * 6;
    const hairS = 1.2;

    // gsap.to(eyeLRef.current, { duration: 1, x: -eyeLX, y: -eyeLY, ease: "expo.out" });
    // gsap.to(eyeRRef.current, { duration: 1, x: -eyeRX, y: -eyeRY, ease: "expo.out" });
    gsap.to(noseRef.current, { duration: 1, x: -noseX, y: -noseY, rotation: mouthR, transformOrigin: "center center", ease: "expo.out" });
    gsap.to(mouthRef.current, { duration: 1, x: -mouthX, y: -mouthY, rotation: mouthR, transformOrigin: "center center", ease: "expo.out" });
    // gsap.to(chinRef.current, { duration: 1, x: -chinX, y: -chinY, scaleY: chinS, ease: "expo.out" });
    gsap.to(faceRef.current, { duration: 1, x: -faceX, y: -faceY, skewX: -faceSkew, transformOrigin: "center top", ease: "expo.out" });
    gsap.to(eyebrowRef.current, { duration: 1, x: -faceX, y: -faceY, skewX: -eyebrowSkew, transformOrigin: "center top", ease: "expo.out" });
    gsap.to(outerEarLRef.current, { duration: 1, x: outerEarX, y: -outerEarY, ease: "expo.out" });
    gsap.to(outerEarRRef.current, { duration: 1, x: outerEarX, y: outerEarY, ease: "expo.out" });
    gsap.to(earHairLRef.current, { duration: 1, x: -outerEarX, y: -outerEarY, ease: "expo.out" });
    gsap.to(earHairRRef.current, { duration: 1, x: -outerEarX, y: outerEarY, ease: "expo.out" });
    gsap.to(hairRef.current, { duration: 1, x: hairX, scaleY: hairS, transformOrigin: "center bottom", ease: "expo.out" });

    document.body.removeChild(div);
  };

  const onUsernameInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    getCoord();
    const value = e.target.value;

    if (value.length > 0) {
      if (mouthStatus === "small") {
        mouthStatus = "medium";
        if (mouthMediumBGRef.current) {
          gsap.to([mouthBGRef.current, mouthOutlineRef.current], { 
            duration: 1, 
            morphSVG: mouthMediumBGRef.current, 
            ease: "expo.out" 
          });
        }
        gsap.to(toothRef.current, { duration: 1, x: 0, y: 0, ease: "expo.out" });
        gsap.to(tongueRef.current, { duration: 1, x: 0, y: 1, ease: "expo.out" });
        gsap.to([eyeLRef.current, eyeRRef.current], { duration: 1, scaleX: 0.85, scaleY: 0.85, ease: "expo.out" });
      }
    } else {
      mouthStatus = "small";
      if (mouthSmallBGRef.current) {
        gsap.to([mouthBGRef.current, mouthOutlineRef.current], { 
          duration: 1, 
          morphSVG: mouthSmallBGRef.current, 
          ease: "expo.out" 
        });
      }
      gsap.to(toothRef.current, { duration: 1, x: 0, y: 0, ease: "expo.out" });
      gsap.to(tongueRef.current, { duration: 1, y: 0, ease: "expo.out" });
      gsap.to([eyeLRef.current, eyeRRef.current], { duration: 1, scaleX: 1, scaleY: 1, ease: "expo.out" });
    }
  };

  const onUsernameFocus = () => {
    usernameRef.current?.parentElement?.classList.add("focusWithText");
    getCoord();
  };

  const onUsernameBlur = () => {
    if (usernameRef.current?.value === "") {
      usernameRef.current?.parentElement?.classList.remove("focusWithText");
    }
    resetFace();
  };

  const onPasswordFocus = () => {
    coverEyes();
  };

  const onPasswordBlur = () => {
    uncoverEyes();
  };

  const coverEyes = () => {
    gsap.to(armLRef.current, { duration: 0.45, x: -93, y: 2, rotation: 0, ease: "quad.out" });
    gsap.to(armRRef.current, { duration: 0.45, x: -93, y: 2, rotation: 0, ease: "quad.out", delay: 0.1 });
  };

  const uncoverEyes = () => {
    gsap.to(armLRef.current, { duration: 1.35, y: 220, ease: "quad.out" });
    gsap.to(armLRef.current, { duration: 1.35, rotation: 105, ease: "quad.out", delay: 0.1 });
    gsap.to(armRRef.current, { duration: 1.35, y: 220, ease: "quad.out" });
    gsap.to(armRRef.current, { duration: 1.35, rotation: -105, ease: "quad.out", delay: 0.1 });
  };

  const resetFace = () => {
    gsap.to([eyeLRef.current, eyeRRef.current], { duration: 1, x: 0, y: 0, ease: "expo.out" });
    gsap.to(noseRef.current, { duration: 1, x: 0, y: 0, scaleX: 1, scaleY: 1, ease: "expo.out" });
    gsap.to(mouthRef.current, { duration: 1, x: 0, y: 0, rotation: 0, ease: "expo.out" });
    gsap.to(chinRef.current, { duration: 1, x: 0, y: 0, scaleY: 1, ease: "expo.out" });
    gsap.to([faceRef.current, eyebrowRef.current], { duration: 1, x: 0, y: 0, skewX: 0, ease: "expo.out" });
    gsap.to([outerEarLRef.current, outerEarRRef.current, earHairLRef.current, earHairRRef.current, hairRef.current], { 
      duration: 1, 
      x: 0, 
      y: 0, 
      scaleY: 1, 
      ease: "expo.out" 
    });
  };

  const handleLogin = async () => {
    const username = usernameRef.current?.value;
    const password = passwordRef.current?.value;

    if (!username || !password) {
      setError('Username e password sono obbligatori');
      return;
    }

    setError('');
    setIsLoading(true);

    try {
      // Se c'è già un utente loggato, fai logout prima
      try {
        await getCurrentUser();
        await signOut();
      } catch {
        // Nessun utente loggato, va bene
      }

      // Fai il login
      await signIn({ username, password });
      console.log('Login riuscito');
      // Ricarica la pagina per far ricontrollare l'auth
      window.location.href = '/dashboard';
    } catch (err: any) {
      console.error('Errore login:', err);
      if (err.name === 'UserAlreadyAuthenticatedException') {
        // Se l'utente è già autenticato, vai alla dashboard
        window.location.href = '/dashboard';
      } else {
        setError(err.message || 'Errore durante il login');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleLogin();
  };

  return (
    <div className="login-container">
      <form className="login-form" onSubmit={handleSubmit}>
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <svg version="1.0" preserveAspectRatio="xMidYMid meet" height="63" viewBox="0 0 187.5 47.25" width="250" xmlns="http://www.w3.org/2000/svg">
            <g fill="#000000">
              <g transform="translate(9.485276, 33.384847)">
                <path d="M 19.421875 -4.828125 L 9.21875 -4.828125 L 7.59375 0 L 0.625 0 L 10.515625 -27.328125 L 18.21875 -27.328125 L 28.109375 0 L 21.0625 0 Z M 17.703125 -9.96875 L 14.328125 -19.96875 L 10.96875 -9.96875 Z M 17.703125 -9.96875"/>
              </g>
              <g transform="translate(38.165649, 33.384847)">
                <path d="M 1.09375 -10.890625 C 1.09375 -13.128906 1.515625 -15.09375 2.359375 -16.78125 C 3.203125 -18.46875 4.347656 -19.765625 5.796875 -20.671875 C 7.253906 -21.578125 8.878906 -22.03125 10.671875 -22.03125 C 12.097656 -22.03125 13.398438 -21.726562 14.578125 -21.125 C 15.753906 -20.53125 16.679688 -19.726562 17.359375 -18.71875 L 17.359375 -28.796875 L 24.015625 -28.796875 L 24.015625 0 L 17.359375 0 L 17.359375 -3.109375 C 16.734375 -2.078125 15.84375 -1.25 14.6875 -0.625 C 13.539062 0 12.203125 0.3125 10.671875 0.3125 C 8.878906 0.3125 7.253906 -0.144531 5.796875 -1.0625 C 4.347656 -1.988281 3.203125 -3.300781 2.359375 -5 C 1.515625 -6.695312 1.09375 -8.660156 1.09375 -10.890625 Z M 17.359375 -10.859375 C 17.359375 -12.515625 16.894531 -13.820312 15.96875 -14.78125 C 15.050781 -15.75 13.929688 -16.234375 12.609375 -16.234375 C 11.285156 -16.234375 10.160156 -15.757812 9.234375 -14.8125 C 8.316406 -13.863281 7.859375 -12.554688 7.859375 -10.890625 C 7.859375 -9.234375 8.316406 -7.914062 9.234375 -6.9375 C 10.160156 -5.96875 11.285156 -5.484375 12.609375 -5.484375 C 13.929688 -5.484375 15.050781 -5.960938 15.96875 -6.921875 C 16.894531 -7.890625 17.359375 -9.203125 17.359375 -10.859375 Z M 17.359375 -10.859375"/>
              </g>
              <g transform="translate(64.588948, 33.384847)">
                <path d="M 5.765625 -23.96875 C 4.597656 -23.96875 3.644531 -24.3125 2.90625 -25 C 2.164062 -25.6875 1.796875 -26.539062 1.796875 -27.5625 C 1.796875 -28.59375 2.164062 -29.453125 2.90625 -30.140625 C 3.644531 -30.828125 4.597656 -31.171875 5.765625 -31.171875 C 6.898438 -31.171875 7.835938 -30.828125 8.578125 -30.140625 C 9.316406 -29.453125 9.6875 -28.59375 9.6875 -27.5625 C 9.6875 -26.539062 9.316406 -25.6875 8.578125 -25 C 7.835938 -24.3125 6.898438 -23.96875 5.765625 -23.96875 Z M 9.0625 -21.71875 L 9.0625 0 L 2.40625 0 L 2.40625 -21.71875 Z M 9.0625 -21.71875"/>
              </g>
              <g transform="translate(76.068877, 33.384847)">
                <path d="M 18.953125 -14.015625 C 20.535156 -13.671875 21.804688 -12.882812 22.765625 -11.65625 C 23.722656 -10.425781 24.203125 -9.019531 24.203125 -7.4375 C 24.203125 -5.15625 23.40625 -3.34375 21.8125 -2 C 20.21875 -0.664062 17.992188 0 15.140625 0 L 2.40625 0 L 2.40625 -27.328125 L 14.71875 -27.328125 C 17.488281 -27.328125 19.660156 -26.691406 21.234375 -25.421875 C 22.804688 -24.148438 23.59375 -22.421875 23.59375 -20.234375 C 23.59375 -18.628906 23.171875 -17.296875 22.328125 -16.234375 C 21.484375 -15.171875 20.359375 -14.429688 18.953125 -14.015625 Z M 9.0625 -16.265625 L 13.421875 -16.265625 C 14.515625 -16.265625 15.351562 -16.503906 15.9375 -16.984375 C 16.519531 -17.460938 16.8125 -18.171875 16.8125 -19.109375 C 16.8125 -20.046875 16.519531 -20.757812 15.9375 -21.25 C 15.351562 -21.738281 14.515625 -21.984375 13.421875 -21.984375 L 9.0625 -21.984375 Z M 13.96875 -5.375 C 15.082031 -5.375 15.941406 -5.625 16.546875 -6.125 C 17.160156 -6.632812 17.46875 -7.367188 17.46875 -8.328125 C 17.46875 -9.285156 17.148438 -10.035156 16.515625 -10.578125 C 15.878906 -11.128906 15.003906 -11.40625 13.890625 -11.40625 L 9.0625 -11.40625 L 9.0625 -5.375 Z M 13.96875 -5.375"/>
              </g>
              <g transform="translate(101.713878, 33.384847)">
                <path d="M 12.296875 0.3125 C 10.171875 0.3125 8.257812 -0.140625 6.5625 -1.046875 C 4.863281 -1.953125 3.523438 -3.25 2.546875 -4.9375 C 1.578125 -6.625 1.09375 -8.597656 1.09375 -10.859375 C 1.09375 -13.085938 1.582031 -15.050781 2.5625 -16.75 C 3.550781 -18.457031 4.898438 -19.765625 6.609375 -20.671875 C 8.328125 -21.578125 10.25 -22.03125 12.375 -22.03125 C 14.5 -22.03125 16.414062 -21.578125 18.125 -20.671875 C 19.84375 -19.765625 21.195312 -18.457031 22.1875 -16.75 C 23.175781 -15.050781 23.671875 -13.085938 23.671875 -10.859375 C 23.671875 -8.628906 23.171875 -6.660156 22.171875 -4.953125 C 21.171875 -3.253906 19.804688 -1.953125 18.078125 -1.046875 C 16.347656 -0.140625 14.421875 0.3125 12.296875 0.3125 Z M 12.296875 -5.453125 C 13.566406 -5.453125 14.648438 -5.914062 15.546875 -6.84375 C 16.441406 -7.78125 16.890625 -9.117188 16.890625 -10.859375 C 16.890625 -12.597656 16.453125 -13.929688 15.578125 -14.859375 C 14.710938 -15.796875 13.644531 -16.265625 12.375 -16.265625 C 11.082031 -16.265625 10.003906 -15.800781 9.140625 -14.875 C 8.285156 -13.957031 7.859375 -12.617188 7.859375 -10.859375 C 7.859375 -9.117188 8.28125 -7.78125 9.125 -6.84375 C 9.96875 -5.914062 11.023438 -5.453125 12.296875 -5.453125 Z M 12.296875 -5.453125"/>
              </g>
              <g transform="translate(126.502753, 33.384847)">
                <path d="M 1.09375 -10.890625 C 1.09375 -13.128906 1.515625 -15.09375 2.359375 -16.78125 C 3.203125 -18.46875 4.347656 -19.765625 5.796875 -20.671875 C 7.253906 -21.578125 8.878906 -22.03125 10.671875 -22.03125 C 12.097656 -22.03125 13.398438 -21.726562 14.578125 -21.125 C 15.753906 -20.53125 16.679688 -19.726562 17.359375 -18.71875 L 17.359375 -28.796875 L 24.015625 -28.796875 L 24.015625 0 L 17.359375 0 L 17.359375 -3.109375 C 16.734375 -2.078125 15.84375 -1.25 14.6875 -0.625 C 13.539062 0 12.203125 0.3125 10.671875 0.3125 C 8.878906 0.3125 7.253906 -0.144531 5.796875 -1.0625 C 4.347656 -1.988281 3.203125 -3.300781 2.359375 -5 C 1.515625 -6.695312 1.09375 -8.660156 1.09375 -10.890625 Z M 17.359375 -10.859375 C 17.359375 -12.515625 16.894531 -13.820312 15.96875 -14.78125 C 15.050781 -15.75 13.929688 -16.234375 12.609375 -16.234375 C 11.285156 -16.234375 10.160156 -15.757812 9.234375 -14.8125 C 8.316406 -13.863281 7.859375 -12.554688 7.859375 -10.890625 C 7.859375 -9.234375 8.316406 -7.914062 9.234375 -6.9375 C 10.160156 -5.96875 11.285156 -5.484375 12.609375 -5.484375 C 13.929688 -5.484375 15.050781 -5.960938 15.96875 -6.921875 C 16.894531 -7.890625 17.359375 -9.203125 17.359375 -10.859375 Z M 17.359375 -10.859375"/>
              </g>
              <g transform="translate(152.926052, 33.384847)">
                <path d="M 24.59375 -21.71875 L 10.96875 10.3125 L 3.8125 10.3125 L 8.796875 -0.734375 L -0.03125 -21.71875 L 7.390625 -21.71875 L 12.421875 -8.140625 L 17.390625 -21.71875 Z M 24.59375 -21.71875"/>
              </g>
            </g>
          </svg>
        </div>
        <div className="svgContainer">
          <div>
            <svg ref={svgRef} className="mySVG" xmlns="http://www.w3.org/2000/svg" xmlnsXlink="http://www.w3.org/1999/xlink" viewBox="0 0 200 200">
              <defs>
                <circle id="armMaskPath" cx="100" cy="100" r="100"/>
              </defs>
              <clipPath id="armMask">
                <use xlinkHref="#armMaskPath" overflow="visible"/>
              </clipPath>
              <circle cx="100" cy="100" r="100" fill="#efc9a7"/>
              <g className="body">
                <path fill="#FFFFFF" d="M193.3,135.9c-5.8-8.4-15.5-13.9-26.5-13.9H151V72c0-27.6-22.4-50-50-50S51,44.4,51,72v50H32.1 c-10.6,0-20,5.1-25.8,13l0,78h187L193.3,135.9z"/>
                <path fill="none" stroke="#6b4a2f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" d="M193.3,135.9 c-5.8-8.4-15.5-13.9-26.5-13.9H151V72c0-27.6-22.4-50-50-50S51,44.4,51,72v50H32.1c-10.6,0-20,5.1-25.8,13"/>
                <path fill="#f9ede3" d="M100,156.4c-22.9,0-43,11.1-54.1,27.7c15.6,10,34.2,15.9,54.1,15.9s38.5-5.8,54.1-15.9 C143,167.5,122.9,156.4,100,156.4z"/>
              </g>
              <g className="earL">
                <g ref={outerEarLRef} className="outerEar" fill="#f9ede3" stroke="#6b4a2f" strokeWidth="2.5">
                  <circle cx="47" cy="83" r="11.5"/>
                  <path d="M46.3 78.9c-2.3 0-4.1 1.9-4.1 4.1 0 2.3 1.9 4.1 4.1 4.1" strokeLinecap="round" strokeLinejoin="round"/>
                </g>
                <g ref={earHairLRef} className="earHair">
                  <rect x="51" y="64" fill="#FFFFFF" width="15" height="35"/>
                  <path d="M53.4 62.8C48.5 67.4 45 72.2 42.8 77c3.4-.1 6.8-.1 10.1.1-4 3.7-6.8 7.6-8.2 11.6 2.1 0 4.2 0 6.3.2-2.6 4.1-3.8 8.3-3.7 12.5 1.2-.7 3.4-1.4 5.2-1.9" fill="#fff" stroke="#6b4a2f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                </g>
              </g>
              <g className="earR">
                <g ref={outerEarRRef} className="outerEar" fill="#f9ede3" stroke="#6b4a2f" strokeWidth="2.5">
                  <circle cx="155" cy="83" r="11.5"/>
                  <path d="M155.7 78.9c2.3 0 4.1 1.9 4.1 4.1 0 2.3-1.9 4.1-4.1 4.1" strokeLinecap="round" strokeLinejoin="round"/>
                </g>
                <g ref={earHairRRef} className="earHair">
                  <rect x="131" y="64" fill="#FFFFFF" width="20" height="35"/>
                  <path d="M148.6 62.8c4.9 4.6 8.4 9.4 10.6 14.2-3.4-.1-6.8-.1-10.1.1 4 3.7 6.8 7.6 8.2 11.6-2.1 0-4.2 0-6.3.2 2.6 4.1 3.8 8.3 3.7 12.5-1.2-.7-3.4-1.4-5.2-1.9" fill="#fff" stroke="#6b4a2f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                </g>
              </g>
              <path ref={chinRef} className="chin" d="M84.1 121.6c2.7 2.9 6.1 5.4 9.8 7.5l.9-4.5c2.9 2.5 6.3 4.8 10.2 6.5 0-1.9-.1-3.9-.2-5.8 3 1.2 6.2 2 9.7 2.5-.3-2.1-.7-4.1-1.2-6.1" fill="none" stroke="#6b4a2f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path ref={faceRef} className="face" fill="#f9ede3" d="M134.5,46v35.5c0,21.815-15.446,39.5-34.5,39.5s-34.5-17.685-34.5-39.5V46"/>
              <path ref={hairRef} className="hair" fill="#FFFFFF" stroke="#6b4a2f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" d="M81.457,27.929 c1.755-4.084,5.51-8.262,11.253-11.77c0.979,2.565,1.883,5.14,2.712,7.723c3.162-4.265,8.626-8.27,16.272-11.235 c-0.737,3.293-1.588,6.573-2.554,9.837c4.857-2.116,11.049-3.64,18.428-4.156c-2.403,3.23-5.021,6.391-7.852,9.474"/>
              <g ref={eyebrowRef} className="eyebrow">
                <path fill="#FFFFFF" d="M138.142,55.064c-4.93,1.259-9.874,2.118-14.787,2.599c-0.336,3.341-0.776,6.689-1.322,10.037 c-4.569-1.465-8.909-3.222-12.996-5.226c-0.98,3.075-2.07,6.137-3.267,9.179c-5.514-3.067-10.559-6.545-15.097-10.329 c-1.806,2.889-3.745,5.73-5.816,8.515c-7.916-4.124-15.053-9.114-21.296-14.738l1.107-11.768h73.475V55.064z"/>
                <path fill="#FFFFFF" stroke="#6b4a2f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" d="M63.56,55.102 c6.243,5.624,13.38,10.614,21.296,14.738c2.071-2.785,4.01-5.626,5.816-8.515c4.537,3.785,9.583,7.263,15.097,10.329 c1.197-3.043,2.287-6.104,3.267-9.179c4.087,2.004,8.427,3.761,12.996,5.226c0.545-3.348,0.986-6.696,1.322-10.037 c4.913-0.481,9.857-1.34,14.787-2.599"/>
              </g>
              <g ref={eyeLRef} className="eyeL">
                <circle cx="85.5" cy="78.5" r="3.5" fill="#6b4a2f"/>
                <circle cx="84" cy="76" r="1" fill="#fff"/>
              </g>
              <g ref={eyeRRef} className="eyeR">
                <circle cx="114.5" cy="78.5" r="3.5" fill="#6b4a2f"/>
                <circle cx="113" cy="76" r="1" fill="#fff"/>
              </g>
              <g ref={mouthRef} className="mouth">
                <path ref={mouthBGRef} className="mouthBG" fill="#617E92" d="M100.2,101c-0.4,0-1.4,0-1.8,0c-2.7-0.3-5.3-1.1-8-2.5c-0.7-0.3-0.9-1.2-0.6-1.8 c0.2-0.5,0.7-0.7,1.2-0.7c0.2,0,0.5,0.1,0.6,0.2c3,1.5,5.8,2.3,8.6,2.3s5.7-0.7,8.6-2.3c0.2-0.1,0.4-0.2,0.6-0.2 c0.5,0,1,0.3,1.2,0.7c0.4,0.7,0.1,1.5-0.6,1.9c-2.6,1.4-5.3,2.2-7.9,2.5C101.7,101,100.5,101,100.2,101z"/>
                <path ref={mouthSmallBGRef} style={{ display: 'none' }} className="mouthSmallBG" fill="#617E92" d="M100.2,101c-0.4,0-1.4,0-1.8,0c-2.7-0.3-5.3-1.1-8-2.5c-0.7-0.3-0.9-1.2-0.6-1.8 c0.2-0.5,0.7-0.7,1.2-0.7c0.2,0,0.5,0.1,0.6,0.2c3,1.5,5.8,2.3,8.6,2.3s5.7-0.7,8.6-2.3c0.2-0.1,0.4-0.2,0.6-0.2 c0.5,0,1,0.3,1.2,0.7c0.4,0.7,0.1,1.5-0.6,1.9c-2.6,1.4-5.3,2.2-7.9,2.5C101.7,101,100.5,101,100.2,101z"/>
                <path ref={mouthMediumBGRef} style={{ display: 'none' }} className="mouthMediumBG" d="M95,104.2c-4.5,0-8.2-3.7-8.2-8.2v-2c0-1.2,1-2.2,2.2-2.2h22c1.2,0,2.2,1,2.2,2.2v2 c0,4.5-3.7,8.2-8.2,8.2H95z"/>
                <path ref={mouthLargeBGRef} style={{ display: 'none' }} className="mouthLargeBG" d="M100 110.2c-9 0-16.2-7.3-16.2-16.2 0-2.3 1.9-4.2 4.2-4.2h24c2.3 0 4.2 1.9 4.2 4.2 0 9-7.2 16.2-16.2 16.2z" fill="#617e92" stroke="#6b4a2f" strokeLinejoin="round" strokeWidth="2.5"/>
                <defs>
                  <path id="mouthMaskPath2" d="M100.2,101c-0.4,0-1.4,0-1.8,0c-2.7-0.3-5.3-1.1-8-2.5c-0.7-0.3-0.9-1.2-0.6-1.8 c0.2-0.5,0.7-0.7,1.2-0.7c0.2,0,0.5,0.1,0.6,0.2c3,1.5,5.8,2.3,8.6,2.3s5.7-0.7,8.6-2.3c0.2-0.1,0.4-0.2,0.6-0.2 c0.5,0,1,0.3,1.2,0.7c0.4,0.7,0.1,1.5-0.6,1.9c-2.6,1.4-5.3,2.2-7.9,2.5C101.7,101,100.5,101,100.2,101z"/>
                </defs>
                <clipPath id="mouthMask">
                  <use xlinkHref="#mouthMaskPath2" overflow="visible"/>
                </clipPath>
                <g clipPath="url(#mouthMask)">
                  <g ref={tongueRef} className="tongue">
                    <circle cx="100" cy="107" r="8" fill="#cc4a6c"/>
                    <ellipse className="tongueHighlight" cx="100" cy="100.5" rx="3" ry="1.5" opacity=".1" fill="#fff"/>
                  </g>
                </g>
                <path ref={toothRef} clipPath="url(#mouthMask)" className="tooth" style={{ fill: '#FFFFFF' }} d="M106,97h-4c-1.1,0-2-0.9-2-2v-2h8v2C108,96.1,107.1,97,106,97z"/>
                <path ref={mouthOutlineRef} className="mouthOutline" fill="none" stroke="#6b4a2f" strokeWidth="2.5" strokeLinejoin="round" d="M100.2,101c-0.4,0-1.4,0-1.8,0c-2.7-0.3-5.3-1.1-8-2.5c-0.7-0.3-0.9-1.2-0.6-1.8 c0.2-0.5,0.7-0.7,1.2-0.7c0.2,0,0.5,0.1,0.6,0.2c3,1.5,5.8,2.3,8.6,2.3s5.7-0.7,8.6-2.3c0.2-0.1,0.4-0.2,0.6-0.2 c0.5,0,1,0.3,1.2,0.7c0.4,0.7,0.1,1.5-0.6,1.9c-2.6,1.4-5.3,2.2-7.9,2.5C101.7,101,100.5,101,100.2,101z"/>
              </g>
              <path ref={noseRef} className="nose" d="M97.7 79.9h4.7c1.9 0 3 2.2 1.9 3.7l-2.3 3.3c-.9 1.3-2.9 1.3-3.8 0l-2.3-3.3c-1.3-1.6-.2-3.7 1.8-3.7z" fill="#6b4a2f"/>
              <g className="arms" clipPath="url(#armMask)">
                <g ref={armLRef} className="armL">
                  <path fill="#f9ede3" stroke="#6b4a2f" strokeLinecap="round" strokeLinejoin="round" strokeMiterlimit="10" strokeWidth="2.5" d="M121.3 97.4L111 58.7l38.8-10.4 20 36.1z"/>
                  <path fill="#f9ede3" stroke="#6b4a2f" strokeLinecap="round" strokeLinejoin="round" strokeMiterlimit="10" strokeWidth="2.5" d="M134.4 52.5l19.3-5.2c2.7-.7 5.4.9 6.1 3.5.7 2.7-.9 5.4-3.5 6.1L146 59.7M160.8 76.5l19.4-5.2c2.7-.7 5.4.9 6.1 3.5.7 2.7-.9 5.4-3.5 6.1l-18.3 4.9M158.3 66.8l23.1-6.2c2.7-.7 5.4.9 6.1 3.5.7 2.7-.9 5.4-3.5 6.1l-23.1 6.2M150.9 58.4l26-7c2.7-.7 5.4.9 6.1 3.5.7 2.7-.9 5.4-3.5 6.1l-21.3 5.7"/>
                  <path fill="#efc9a7" d="M178.8 74.7l2.2-.6c1.1-.3 2.2.3 2.4 1.4.3 1.1-.3 2.2-1.4 2.4l-2.2.6-1-3.8zM180.1 64l2.2-.6c1.1-.3 2.2.3 2.4 1.4.3 1.1-.3 2.2-1.4 2.4l-2.2.6-1-3.8zM175.5 54.9l2.2-.6c1.1-.3 2.2.3 2.4 1.4.3 1.1-.3 2.2-1.4 2.4l-2.2.6-1-3.8zM152.1 49.4l2.2-.6c1.1-.3 2.2.3 2.4 1.4.3 1.1-.3 2.2-1.4 2.4l-2.2.6-1-3.8z"/>
                  <path fill="#fff" stroke="#6b4a2f" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M123.5 96.8c-41.4 14.9-84.1 30.7-108.2 35.5L1.2 80c33.5-9.9 71.9-16.5 111.9-21.8"/>
                  <path fill="#fff" stroke="#6b4a2f" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M108.5 59.4c7.7-5.3 14.3-8.4 22.8-13.2-2.4 5.3-4.7 10.3-6.7 15.1 4.3.3 8.4.7 12.3 1.3-4.2 5-8.1 9.6-11.5 13.9 3.1 1.1 6 2.4 8.7 3.8-1.4 2.9-2.7 5.8-3.9 8.5 2.5 3.5 4.6 7.2 6.3 11-4.9-.8-9-.7-16.2-2.7M94.5 102.8c-.6 4-3.8 8.9-9.4 14.7-2.6-1.8-5-3.7-7.2-5.7-2.5 4.1-6.6 8.8-12.2 14-1.9-2.2-3.4-4.5-4.5-6.9-4.4 3.3-9.5 6.9-15.4 10.8-.2-3.4.1-7.1 1.1-10.9M97.5 62.9c-1.7-2.4-5.9-4.1-12.4-5.2-.9 2.2-1.8 4.3-2.5 6.5-3.8-1.8-9.4-3.1-17-3.8.5 2.3 1.2 4.5 1.9 6.8-5-.6-11.2-.9-18.4-1 2 2.9.9 3.5 3.9 6.2"/>
                </g>
                <g ref={armRRef} className="armR">
                  <path fill="#f9ede3" stroke="#6b4a2f" strokeLinecap="round" strokeLinejoin="round" strokeMiterlimit="10" strokeWidth="2.5" d="M265.4 97.3l10.4-38.6-38.9-10.5-20 36.1z"/>
                  <path fill="#f9ede3" stroke="#6b4a2f" strokeLinecap="round" strokeLinejoin="round" strokeMiterlimit="10" strokeWidth="2.5" d="M252.4 52.4L233 47.2c-2.7-.7-5.4.9-6.1 3.5-.7 2.7.9 5.4 3.5 6.1l10.3 2.8M226 76.4l-19.4-5.2c-2.7-.7-5.4.9-6.1 3.5-.7 2.7.9 5.4 3.5 6.1l18.3 4.9M228.4 66.7l-23.1-6.2c-2.7-.7-5.4.9-6.1 3.5-.7 2.7.9 5.4 3.5 6.1l23.1 6.2M235.8 58.3l-26-7c-2.7-.7-5.4.9-6.1 3.5-.7 2.7.9 5.4 3.5 6.1l21.3 5.7"/>
                  <path fill="#efc9a7" d="M207.9 74.7l-2.2-.6c-1.1-.3-2.2.3-2.4 1.4-.3 1.1.3 2.2 1.4 2.4l2.2.6 1-3.8zM206.7 64l-2.2-.6c-1.1-.3-2.2.3-2.4 1.4-.3 1.1.3 2.2 1.4 2.4l2.2.6 1-3.8zM211.2 54.8l-2.2-.6c-1.1-.3-2.2.3-2.4 1.4-.3 1.1.3 2.2 1.4 2.4l2.2.6 1-3.8zM234.6 49.4l-2.2-.6c-1.1-.3-2.2.3-2.4 1.4-.3 1.1.3 2.2 1.4 2.4l2.2.6 1-3.8z"/>
                  <path fill="#fff" stroke="#6b4a2f" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M263.3 96.7c41.4 14.9 84.1 30.7 108.2 35.5l14-52.3C352 70 313.6 63.5 273.6 58.1"/>
                  <path fill="#fff" stroke="#6b4a2f" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M278.2 59.3l-18.6-10 2.5 11.9-10.7 6.5 9.9 8.7-13.9 6.4 9.1 5.9-13.2 9.2 23.1-.9M284.5 100.1c-.4 4 1.8 8.9 6.7 14.8 3.5-1.8 6.7-3.6 9.7-5.5 1.8 4.2 5.1 8.9 10.1 14.1 2.7-2.1 5.1-4.4 7.1-6.8 4.1 3.4 9 7 14.7 11 1.2-3.4 1.8-7 1.7-10.9M314 66.7s5.4-5.7 12.6-7.4c1.7 2.9 3.3 5.7 4.9 8.6 3.8-2.5 9.8-4.4 18.2-5.7.1 3.1.1 6.1 0 9.2 5.5-1 12.5-1.6 20.8-1.9-1.4 3.9-2.5 8.4-2.5 8.4"/>
                </g>
              </g>
            </svg>
          </div>
        </div>
        
        <div className="inputGroup inputGroup1">
          <label htmlFor="username">Username</label>
          <input 
            ref={usernameRef}
            type="text" 
            id="username" 
            className="username" 
            maxLength={256}
            onFocus={onUsernameFocus}
            onBlur={onUsernameBlur}
            onInput={onUsernameInput}
          />
          <span className="indicator"></span>
        </div>
        <div className="inputGroup inputGroup2">
          <label htmlFor="password">Password</label>
          <input 
            ref={passwordRef}
            type="password" 
            id="password" 
            className="password"
            onFocus={onPasswordFocus}
            onBlur={onPasswordBlur}
          />
        </div>
        {error && (
          <div style={{ color: '#cc4a6c', marginBottom: '1em', fontSize: '0.9em', textAlign: 'center' }}>
            {error}
          </div>
        )}
        <div className="inputGroup inputGroup3">
          <button type="submit" id="login" disabled={isLoading}>
            {isLoading ? 'Accesso in corso...' : 'Log in'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default Login;
