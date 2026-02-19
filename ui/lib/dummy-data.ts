import { Agent } from '@/types';

export const DUMMY_AGENTS: Agent[] = [
  {
    handle: '@alice.bsky.social',
    name: 'Alice Chen',
    bio: 'AI researcher and educator. Building the future of human-AI collaboration.',
    generatedBio: 'Alice is a passionate AI researcher who focuses on making artificial intelligence more accessible and understandable. She regularly shares insights about machine learning, human-computer interaction, and the ethical implications of AI technology.',
    followers: 12450,
    following: 892,
    postsCount: 3421,
  },
  {
    handle: '@bob.tech',
    name: 'Bob Martinez',
    bio: 'Software engineer | Open source contributor | Coffee enthusiast ☕',
    generatedBio: 'Bob is an experienced software engineer with a strong focus on open-source contributions. He loves sharing technical knowledge, code reviews, and occasionally posts about his coffee adventures.',
    followers: 8765,
    following: 1203,
    postsCount: 2105,
  },
  {
    handle: '@charlie.dev',
    name: 'Charlie Kim',
    bio: 'Building products that matter. Former startup founder.',
    generatedBio: 'Charlie is a product-focused engineer with a background in startup entrepreneurship. He shares lessons learned, product development insights, and thoughts on building sustainable businesses.',
    followers: 15432,
    following: 567,
    postsCount: 4521,
  },
  {
    handle: '@diana.design',
    name: 'Diana Park',
    bio: 'UX Designer | Accessibility advocate | Design systems enthusiast',
    generatedBio: 'Diana is a UX designer passionate about creating inclusive and accessible digital experiences. She frequently shares design system patterns, accessibility best practices, and thoughts on how design impacts user behavior.',
    followers: 9876,
    following: 1456,
    postsCount: 1876,
  },
  {
    handle: '@edward.data',
    name: 'Edward Wu',
    bio: 'Data scientist | ML engineer | Stats nerd 📊',
    generatedBio: 'Edward is a data scientist who loves diving deep into datasets and building machine learning models. He shares analysis insights, statistical findings, and practical ML techniques with the community.',
    followers: 11234,
    following: 789,
    postsCount: 3210,
  },
  {
    handle: '@fiona.frontend',
    name: 'Fiona Lee',
    bio: 'Frontend engineer | React enthusiast | CSS wizard',
    generatedBio: 'Fiona is a frontend engineer specializing in React and modern CSS. She enjoys building performant web applications and sharing tips on component architecture, performance optimization, and creative CSS techniques.',
    followers: 6543,
    following: 923,
    postsCount: 1567,
  },
  {
    handle: '@george.backend',
    name: 'George Thompson',
    bio: 'Backend engineer | Distributed systems | Database optimization',
    generatedBio: 'George is a backend engineer with expertise in distributed systems and database design. He shares insights on system architecture, scalability challenges, and database performance tuning strategies.',
    followers: 14567,
    following: 612,
    postsCount: 2890,
  },
  {
    handle: '@hannah.ai',
    name: 'Hannah Rodriguez',
    bio: 'AI product manager | ML adoption | Ethical AI',
    generatedBio: 'Hannah is a product manager focused on bringing AI products to market. She writes about ML adoption strategies, ethical considerations in AI development, and bridging the gap between technical teams and business stakeholders.',
    followers: 8765,
    following: 1345,
    postsCount: 2103,
  },
];

export function getAgentByHandle(handle: string): Agent | undefined {
  return DUMMY_AGENTS.find((a) => a.handle === handle);
}

